---
title: About
---

*IfState* is a python3 library to configure (linux) host interfaces in a
declarative manner. It is a frontend for the kernel netlink protocol using
[pyroute2](https://pyroute2.org/) and aims to be as powerful as the following commands:

- from iproute2:
  - `ip address`
  - `ip link`
  - `ip route`
  - `ip rule`
- ethtool
- sysctl for interface settings (`/proc/sys/net/ipv[46]/conf/$IFACE/`)
- wireguard

It was written for interface configuration on lightweight software defined linux
routers **without** using any additional network management daemon like
[Network-Manager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) or
[systemd-networkd](https://www.freedesktop.org/software/systemd/man/systemd-networkd.service.html).
Can be used with deployment and automation tools like
[ansible](https://github.com/ansible/ansible) since it's declarative and
operates idempotent.

When *IfState* was born there where already other projects for declarative
interface configuration. Sadly they require network management daemon and lack
support for many virtual link types:
- [NMState](https://nmstate.io) - A Declarative API for Host Network Management
- [Netplan](https://netplan.io) - The network configuration abstraction renderer

*IfState* can be used as a base for dynamic routing daemons like:
- [BIRD](https://bird.network.cz/) - Internet Routing Daemon
- [FRR](https://frrouting.org/) - The FRRouting Protocol Suite
- [Quagga](https://www.quagga.net/) - Routing Software Suite

It is possible to skip different settings (addresses, routes, ...) in *IfState*
completely if a routing daemon (*FRR*, *Quagga*) does handle it.


# Installation

*IfState* is available in the following linux distributions:

- [Alpine Linux](install.md#Alpine-Linux)

Alternatively you could use *pip3* to install *IfState*:

```bash
pip3 install ifstate
```

This will also install all dependencies if not already statisfied.

[More...](install.md)

# Usage

Be aware that using the `ifstatecli` command will by default **shutdown and remove any interfaces** which are not declared in the configuration. It ships with a build-in ignore list for some well-known interfaces which should not handled by *IfState* (i.e. `docker0`, `veth`, ...).

Example configuration:

```yaml
interfaces:
- name: eth0
  link:
    kind: physical
- name: eth0.10
  addresses:
  - 198.51.100.3/27
  link:
    kind: vlan
    link: eth0
    vlan_id: 10
- name: LOOP
  addresses:
  - 192.0.2.3
  - 2001:db8::3
  link:
    kind: dummy

routing:
  routes:
  - to: 198.51.100.128/25
    via: 198.51.100.1
```

Run the `ifstatecli` command:

```bash
# ifstatecli -c test.yml apply
configuring interface links
 eth0            ok
 eth0.10         add
 LOOP            ok
 eth1            orphan

configuring ip addresses...
 eth0.10         198.51.100.3/27
 LOOP            192.0.2.3/32
 LOOP            2001:db8::3/128

configuring routing table main...
 198.51.100.128/25 add
```

It is possible to create a configuration template from the currently available interfaces using the `ifstatecli show` command.

[More...](cli.md)
