#!/usr/bin/env python
"""
This plugin generates tags file as well as inserts markdown
at the beginning of a file that has tags

@Adopted from
JL Diaz (c) 2019
MIT License
"""
from collections  import defaultdict
from pathlib import Path
from re import search, DOTALL, MULTILINE
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
        ('filename', Type(str, default='tags.md')),
        ('folder', Type(str, default='aux')),
        ('template', Type(str)),
        ('css_name', Type(str, default='.button')),
    )

    def __init__(self):
        self.metadata = []
        self.tag_dict = None
        self.filename = "tags.md"
        self.folder = "aux"
        self.template = None
        self.css_name = ".button"
        self.templ = None

    #pylint: disable=unused-argument
    def on_page_markdown(self, markdown, page, config, files):
        """
        takes markdown, page, config, and files
        currently modifies the markdown to add a button to click to get related tag info
        tag is customizeable by adding css that keys off the `self.css_name`
        """
        if 'tags' in page.meta:
            swap_mark = [f"[{x}](/{str(self.filename).strip('.md')}.html#{x}){{{self.css_name}}}"
                         for x in page.meta['tags']]
            swap_mark.append('\n')
            return f'{" ".join(swap_mark)}{markdown}'
        return markdown

    def on_config(self, config):
        """Load config options"""
        self.filename = Path(self.config.get("filename") or self.filename)
        self.folder = Path(self.config.get("folder") or self.folder)
        self.css_name = self.config.get("css_name")
        # Make sure that the tags folder is absolute, and exists
        if not self.folder.is_absolute():
            self.folder = Path(config["docs_dir"]) / ".." / self.folder
        if not self.folder.exists():
            self.folder.mkdir(parents=True)

        if self.config.get("template"):
            self.template = Path(self.config.get("template"))
        if self.template is None:
            self.template = Path(__file__).parent.joinpath(
                "templates"
            ).joinpath("tags.md.template")
        environment = Environment(
            loader=FileSystemLoader(searchpath=str(self.template.parent))
        )
        self.templ = environment.get_template(str(self.template.name))

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
            path=str(self.filename),
            src_dir=str(self.folder),
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

        with open(str(self.folder / self.filename), "w", encoding='utf-8') as fname:
            fname.write(self.generate_tags_page(self.tag_dict))

# Helper functions
def get_metadata(name, path):
    """Get the metadata off of a file"""
    filename = Path(path) / Path(name)
    with filename.open() as fname:
        match_string = search(r"\A\s*---\n.*\n---", fname.read(), flags=DOTALL | MULTILINE)
        if match_string:
            try:
                metadata = match_string.group(0).strip('---')
                meta = load(metadata, Loader=FullLoader)
                meta.update(filename=name)
                return meta
            except YAMLError as err:
                log.error("Couldn't parse %s yaml due to %s", fname, err)
    return None
