from setuptools import setup, find_packages
from datetime import date


def readme():
    with open("README.md") as f:
        return f.read()


def version():
    with open("libifstate/__init__.py") as fd:
        for line in fd:
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


def install_requires():
    requires = [
        "jsonschema",
        "pyroute2",
        "pyyaml"
    ]

    return requires


setup(
    name="ifstate",
    version=version(),
    description="Manage host interface settings in a declarative manner",
    author="Thomas Liske",
    author_email="thomas@fiasko-nw.net",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://ifstate.net/",
    license="GPL3+",
    packages=find_packages(),
    package_data={
        "libifstate": ["../schema/*.schema.json"],
    },
    install_requires=install_requires(),
    extras_require={
        'shell': [
            'pygments'
        ],
        'wireguard': [
            'wgnlpy'
        ]
    },
    entry_points={
        "console_scripts": ["ifstatecli = ifstate.ifstate:main"]
    },
)
