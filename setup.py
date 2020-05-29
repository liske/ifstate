from setuptools import setup, find_packages
from datetime import date


def readme():
    with open("README.md") as f:
        return f.read()


def requirements():
    req = []
    with open("requirements.txt") as fd:
        for line in fd:
            line.strip()
            if not line.startswith("#"):
                req.append(line)
    return req

def version():
    with open("libifstate/__init__.py") as fd:
        for line in fd:
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")

setup(
    name="ifstate",
    version=version(),
    description="Manage host interface settings in a declarative manner",
    author="Thomas Liske",
    author_email="thomas@fiasko-nw.net",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/liske/ifstate",
    license="GPL3+",
    packages=find_packages(),
    install_requires=[
        "pyroute2",
        "PyYAML",
    ],
    entry_points={
        "console_scripts": ["ifstatecli = ifstate.ifstate:main"]
    },
)
