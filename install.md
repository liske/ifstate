---
title: Install
layout: page
permalink: install/
---

# Alpine Linux


## Alpine Linux ≥ 3.13

*IfState* is available in the *community* repository since *Alpine Linux 3.13*.

If the `wireguard-tools-wg` package is going to be installed it will pull also `py3-wgnlpy` which enables *Wireguard* support in *Ifstate*.

To enable *eXpress Data Path* (XDP) support you need to install `libbpf` (available since *Alpine Linux 3.17+*).

You need to install `py3-pygments` to enable syntax highlighting in ifstate's interactive python shell.

# Manual installation

## Prerequisites

*IfState* depends on *Python3* and the following python packages:
- [pyroute2](https://pyroute2.org/) - Python Netlink library
- [PyYAML](https://pyyaml.org/) - YAML parser and emitter for Python
- [jsonschema](https://github.com/Julian/jsonschema) - An implementation of JSON Schema validation for Python
- [wgnlpy](https://github.com/ArgosyLabs/wgnlpy) - Python netlink connector to WireGuard *(optional)*
- [Pygments](https://pygments.org/) - Python syntax highlighter *(optional)*

*IfState* uses python ctypes to configure XDP. You need to have `libbp.so.1` available to configure XDP.

## PyPI

*IfState* is available at [Python Package Index](https://pypi.org/project/ifstate/).  Use *pip3* for installation:

```bash
pip3 install ifstate
```

This will also install all dependencies if not already statisfied. The optional dependenies can be installed via pip's extra feature:

```bash
pip3 install ifstate[shell,wireguard]
```
