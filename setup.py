"""
Setup the plugin
"""
from setuptools import setup, find_packages
import versioneer

setup(
    version=versioneer.get_version(),
    python_requires='>=3.6',
    install_requires=[
        'mkdocs==1.2.3',
    ],
    packages=find_packages(exclude=['*.tests']),
    package_data={'tags': ['templates/*.md.template']},
    entry_points={
        'mkdocs.plugins': [
            'tags = tags.plugin:TagsPlugin'
        ]
    }
)
