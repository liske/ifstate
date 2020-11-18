# IfState

[![PyPI version](https://badge.fury.io/py/ifstate.svg)](https://badge.fury.io/py/ifstate)

A python library to configure (linux) host interfaces in a declarative manner.
It is a frontend for the kernel netlink protocol using
[pyroute2](https://pyroute2.org/) and aims to be as powerful as the
iproute2/bridge/ethtool/tc/wireguard commands.

It was written for interface configuration on lightweight software defined linux
routers **without** using any additional network management daemon like
[Network-Manager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) or
[systemd-networkd](https://www.freedesktop.org/software/systemd/man/systemd-networkd.service.html).

Can be used with deployment and automation tools like
[ansible](https://github.com/ansible/ansible) since it's declarative and
operates idempotent.

[More...](https://ifstate.net/)
