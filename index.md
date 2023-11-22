---
title: About
---

*IfState* is a python3 utility to configure the Linux network stack in a
declarative manner. It is a frontend for the kernel's netlink protocol based on
[pyroute2](https://pyroute2.org/) and aims to be as powerful as the following commands:

- bridge
- ethtool
- iproute2
  - address
  - link
  - neighbour
  - netns
  - route
  - rule
  - vrf
- sysctl for network config (`/proc/sys/net/ipv[46]/conf/$IFACE/`)
- tc
- wireguard
- xdp-tools

It was written for interface configuration on lightweight software defined linux
routers **without** using any additional network management daemon like
[Network-Manager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) or
[systemd-networkd](https://www.freedesktop.org/software/systemd/man/systemd-networkd.service.html).
Can be used with deployment and automation tools like
[ansible](https://github.com/ansible/ansible) since it's declarative and
operates idempotent.

When *IfState* was born there where already other projects for declarative
interface configuration. Sadly they require network management daemons and lack
support for many virtual link types:
- [NMState](https://nmstate.io) - A Declarative API for Host Network Management
- [Netplan](https://netplan.io) - The network configuration abstraction renderer

*IfState* can be used as a base for dynamic routing daemons like:
- [BIRD](https://bird.network.cz/) - Internet Routing Daemon
- [FRR](https://frrouting.org/) - The FRRouting Protocol Suite
- [Quagga](https://www.quagga.net/) - Routing Software Suite

It is possible to skip different settings (addresses, routes, ...) in *IfState*
completely if a routing daemon (*FRR*, *Quagga*) does handle it.

*IfState* has full support for Linux netns namespaces. This allows to build
firewalls and routers with hard multi-client capability without much effort.
[Alpine Linux](https://wiki.alpinelinux.org/wiki/Netns) is one of the few
(the only?) Linux distributions with native netns support for daemons.

# Presentations

The following recordings of public talks about IfState are available online:

- [Declarative network configuration with ifstate](https://youtu.be/n1ZTGrwXPkY)
  at [AlpineConf 2021](https://alpinelinux.org/conf/) (in English)
- [Deklarative Netzwerkkonfiguration mit IfState](https://media.ccc.de/v/clt23-225-deklarative-netzwerkkonfiguration-mit-ifstate)
  at [Chemnitzer Linux-Tage 2023](https://chemnitzer.linux-tage.de/2023/de/programm/beitrag/225) (in German)


# Installation

*IfState* is available in the following linux distributions:

- [Alpine Linux](install.md#Alpine-Linux)

Alternatively you could use *pip3* to install *IfState*:

```bash
pip3 install ifstate
```

This will also install all python dependencies if not already statisfied.

[More…](install.md)


# Usage

Be aware that using the `ifstatecli` command will by default **shutdown and remove any interfaces** which are not declared in the configuration. It ships with a build-in ignore list for some well-known interfaces which should not handled by *IfState* (i.e. `docker0`, `veth`, ...).

Example configuration:

```yaml
interfaces:
- name: eth0
  addresses: []
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
cleanup orphan interfaces...
   eth1                              orphan

configure interfaces...
 lo
   link                              ok
   addresses                         = 127.0.0.1/8
   addresses                         = ::1/128
 eth0
   link                              ok
 eth0.10
   link                              add
   addresses                         + 198.51.100.3/27
 LOOP
   link                              ok
   addresses                         = 192.0.2.3/32
   addresses                         = 2001:db8::3/128

configure routing...
   main                              + 198.51.100.128/25
```

It is possible to create a configuration template from the currently available interfaces using the `ifstatecli show` command.

[More…](cli.md)

<a rel="me" href="https://ibh.social/@liske"></a>
