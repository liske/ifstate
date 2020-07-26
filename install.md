---
title: Install
---

# Alpine Linux

*IfState* is currently available in the *edge community* repository, only.


## Alpine ≥ 3.12

- enable [repository
  pinning](https://wiki.alpinelinux.org/wiki/Alpine_Linux_package_management#Repository_pinning)
  in `/etc/apk/repositories`:

```perl
http://dl-cdn.alpinelinux.org/alpine/v3.12/main
http://dl-cdn.alpinelinux.org/alpine/v3.12/community
@edgecommunity http://dl-cdn.alpinelinux.org/alpine/edge/community
```
- install *IfState* using `apk add ifstate@edgecommunity`


## Alpine ≤ 3.11

- enable [repository
  pinning](https://wiki.alpinelinux.org/wiki/Alpine_Linux_package_management#Repository_pinning)
  in `/etc/apk/repositories`:

```perl
http://dl-cdn.alpinelinux.org/alpine/v3.11/main
http://dl-cdn.alpinelinux.org/alpine/v3.11/community
@edgecommunity http://dl-cdn.alpinelinux.org/alpine/edge/community
```
- install *IfState* using `apk add ifstate@edgecommunity py3-pyroute2@edgecommunity`


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

