# Overview

*IfState* is a python library to configure (linux) host interfaces in a declarative manner. The configuration is done using the kernels netlink protocol and aims to be as powerful as the iproute2/bridge/ethtool commands.

> *IfState* is in a early development state and not ready for productive use!

It was written for interface configuration on lightweight software defined linux routers **without** using any additional network management daemon like [Network-Manager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) or [systemd-networkd](https://www.freedesktop.org/software/systemd/man/systemd-networkd.service.html). It can be used with deployment tools like ansible since it's declarative and operates idempotent.

When *IfState* was born there where already other projects for declarative interface configuration. Sadly they require network management daemon and lack support for many virtual links (i.e. tunnel types):
- [NMState](https://nmstate.io) - A Declarative API for Host Network Management
- [Netplan](https://netplan.io) - The network configuration abstraction renderer



# Prepration

## Prerequisites

*IfState* depends on Python3 and the following packages:
- [pyroute2](https://pyroute2.org/) - Python Netlink library
- [PyYAML](https://pyyaml.org/) - YAML parser and emitter for Python


## Installation

Use *pip* to install *IfState*:

```
pip3 install ifstate
```

This will also install all dependencies if not already statisfied.


# Usage

Be aware that using the `ifstatecli` command will by default **shutdown and remove any interfaces** which are not declared in the configuration. It ships with a build-in ignore list for some well-known interfaces which should not handled by *IfState* (i.e. `docker0`, `veth`, ...).

Example configuration:

```yaml
interfaces:
- name: eth0
  link:
    kind: physical
    address: 8c:16:45:3c:f1:42
- name: eth0.10
  addresses:
  - 198.51.100.3/27
  link:
    kind: vlan
    link: eth0
    vlan_id: 10
- name: wlan0
  link:
    kind: physical
    state: down
- name: LOOP
  addresses:
  - 192.0.2.3
  - 2001:db8::3
  link:
    kind: dummy
```

Run the `ifstatecli` command:

```
# ifstatecli -c test.yml apply
configuring interface links
 eth0            ok
 eth0.10         add
 wlan0           change
 LOOP            ok
 eth1            orphan
 eth1.20         del

configuring ip addresses...
 eth0.10         198.51.100.3/27
 LOOP            192.0.2.3/32
 LOOP            2001:db8::3/128
```

It is possible to create a configuration template from the currently available interfaces using the `ifstatecli show` command:

```yaml
ignore:
  ipaddr:
  - fe80::/10
  ifname:
  - ^docker\d+
  - ^lo$
  - ^ppp\d+$
  - ^veth
  - ^virbr\d+
interfaces:
- name: eth0
  addresses: []
  link:
    kind: physical
    address: 8c:16:45:3c:f1:42
    state: up
- name: wlan0
  addresses: []
  link:
    kind: physical
    address: 8c:16:54:15:aa:21
    state: down
- name: eth0.10
  addresses:
  - 198.51.100.3/27
  link:
    kind: vlan
    state: up
    vlan_flags:
      state:
        flags: 1
        mask: 4294967295
    vlan_id: 10
    vlan_protocol: 33024
- name: LOOP
  addresses:
  - 192.0.2.3
  - 2001:db8::3
  link:
    kind: dummy
    state: up
```

You should consider to remove options which have not been changed or should be ignored.
