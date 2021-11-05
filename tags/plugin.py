#!/usr/bin/env python
"""
# --------------------------------------------
# Main part of the plugin
#
# JL Diaz (c) 2019
# MIT License
# --------------------------------------------
"""
from collections  import defaultdict
from pathlib import Path
from re import search, DOTALL
from yaml import load, FullLoader, YAMLError
from jinja2 import Environment, FileSystemLoader
from mkdocs.structure.files import File
from mkdocs.plugins import BasePlugin
from mkdocs.config.config_options import Type
from mkdocs.__main__ import log


class TagsPlugin(BasePlugin):
    """
    Creates "tags.md" file containing a list of the pages grouped by tags

    It uses the info in the YAML metadata of each page, for the pages which
    provide a "tags" keyword (whose value is a list of strings)
    """
    config_scheme = (
        ('tags_filename', Type(str, default='tags.md')),
        ('tags_folder', Type(str, default='aux')),
        ('tags_template', Type(str)),
    )

    def __init__(self):
        self.metadata = []
        self.tag_dict = None
        self.tags_filename = "tags.md"
        self.tags_folder = "aux"
        self.tags_template = None
        self.tag_css_name = ".button"
        if self.tags_template is None:
            self.tags_template = Path(__file__).parent.joinpath(
                "templates"
            ).joinpath("tags.md.template")
        environment = Environment(
            loader=FileSystemLoader(searchpath=str(self.tags_template.parent))
        )
        self.templ = environment.get_template(str(self.tags_template.name))

    #pylint: disable=unused-argument
    def on_page_markdown(self, markdown, page, config, files):
        """
        takes markdown, page, config, and files
        currently modifies the markdown to add a button to click to get related tag info
        tag is customizeable by adding css that keys off the `self.tag_css_name`
        """
        if 'tags' in page.meta:
            swap_mark = [f"[{x}](/tags.html#{x}){{{self.tag_css_name}}}" for x in page.meta['tags']]
            swap_mark.append('\n')
            return f'{" ".join(swap_mark)}{markdown}'
        return markdown

    def on_config(self, config):
        """Load config options, not sure if this actually works"""
        self.tags_filename = Path(self.config.get("tags_filename") or self.tags_filename)
        self.tags_folder = Path(self.config.get("tags_folder") or self.tags_folder)
        # Make sure that the tags folder is absolute, and exists
        if not self.tags_folder.is_absolute():
            self.tags_folder = Path(config["docs_dir"]) / ".." / self.tags_folder
        if not self.tags_folder.exists():
            self.tags_folder.mkdir(parents=True)

        if self.config.get("tags_template"):
            self.tags_template = Path(self.config.get("tags_template"))

    def on_files(self, files, config):
        """Load files to check for tags"""
        self.metadata = [
            get_metadata(x.src_path, config['docs_dir'])
            for x in files if x.src_path.endswith(".md")
        ]
        # Create new file with tags
        self.generate_tags_file()
        # New file to add to the build
        newfile = File(
            path=str(self.tags_filename),
            src_dir=str(self.tags_folder),
            dest_dir=config["site_dir"],
            use_directory_urls=False
        )
        files.append(newfile)

    def generate_tags_page(self, data):
        """Generate the tags to be populated on the
        mkdocs tag page"""
        return self.templ.render(
            tags=sorted(data.items(), key=lambda t: t[0].lower()),
        )

    def generate_tags_file(self):
        """Generate a file to be stored on the mkdocs page"""
        sorted_meta = sorted(self.metadata, key=lambda e: e.get("year", 5000) if e else 0)
        self.tag_dict = defaultdict(list)
        for meta in sorted_meta:
            if not meta:
                continue
            if "title" not in meta:
                meta["title"] = meta['filename'].split("/")[-1].strip('.md')
            tags = meta.get("tags", [])
            for tag in tags:
                self.tag_dict[tag].append(meta)

        with open(str(self.tags_folder / self.tags_filename), "w", encoding='utf-8') as fname:
            fname.write(self.generate_tags_page(self.tag_dict))

# Helper functions
def get_metadata(name, path):
    """Get the metadata off of a file"""
    filename = Path(path) / Path(name)
    with filename.open() as fname:
        match_string = search(r"---\n.*\n---", fname.read(), DOTALL)
        if match_string:
            try:
                metadata = match_string.group(0).strip('---')
                meta = load(metadata, Loader=FullLoader)
                meta.update(filename=name)
                return meta
            except YAMLError as err:
                log.error("Couldn't parse %s yaml due to %s", fname, err)
    return None
