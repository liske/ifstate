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


setup(
    name="ifstate",
    version='0.1',
    description="manage host interface settings in a declarative manner",
    author="Thomas Liske",
    author_email="thomas@fiasko-nw.net",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/liske/ifstate",
    license="GPL3+",
    packages=find_packages(),
    install_requires=requirements(),
    entry_points={
        "console_scripts": ["ifstate = ifstate.ifstate:main"]
    },
)
