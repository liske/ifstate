# About

IfState is a python library to configure (linux) host interfaces in a declarative manner. The configuration is done using the kernels netlink protocol.

> IfState is in a early development state and not ready for productive use!

It was written for interface configuration on lightweight software defined linux routers **without**   using any additional network management daemon like [Network-Manager](https://gitlab.freedesktop.org/NetworkManager/NetworkManager) or [systemd-(link|networkd)](https://www.freedesktop.org/software/systemd/man/systemd-networkd.service.html). It can be used with deployment tools like ansible since it's declarative and operates idempotent.


# Install

## Prerequisites

IfState depends on Python3 and the following packages:
- pyroute2
- PyYAML


## Package

Use *pip* to install Ifstate:

```
pip install ifstate
```

This will also install all dependencies if not already statisfied.


# Usage

Be aware that using the `ifstatecli` command will by default **remove or shutdown any interface** which is not declared in the configuration. It ships with a build-in ignore list for some well-known interfaces which should not handled by IfState.

Example configuration:

```yaml
interfaces:
- name: eth0
  link:
    kind: physical
    address: 8c:16:45:3c:f1:42
- name: eth0.10
  link:
    kind: vlan
    link: eth0
    vlan_id: 10
- name: wlan0
  link:
    kind: physical
    state: down
 - name: LOOP
   link:
     kind: dummy
```

Run `ifstatecli`:

```
ifstatecli -c test.yml config
WARNING:ifstate:eth1 is a orphan physical interface => shutdown
WARNING:ifstate:eth1.20 is a orphan virtual interface => remove
```
