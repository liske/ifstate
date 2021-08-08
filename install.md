---
title: Install
---

# Alpine Linux


## Alpine ≥ 3.13

*IfState* is available in the *community* repository since *Alpine 3.13*.


# Manual installation

## Prerequisites

*IfState* depends on *Python3* and the following python packages:
- [pyroute2](https://pyroute2.org/) - Python Netlink library
- [PyYAML](https://pyyaml.org/) - YAML parser and emitter for Python
- [jsonschema](https://github.com/Julian/jsonschema) - An implementation of JSON Schema validation for Python
- [wgnlpy](https://github.com/ArgosyLabs/wgnlpy) - Python netlink connector to WireGuard *(optional)*


## PyPI

*IfState* is available at [Python Package Index](https://pypi.org/project/ifstate/).  Use *pip3* for installation:

```bash
pip3 install ifstate
```

This will also install all dependencies if not already statisfied.

