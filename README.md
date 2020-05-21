# ifstate


## About

*ifstate* manages host interface settings in a declarative manner relying only on *iproute2*.

*ifstate* is simular to:
- [nmstate](https://www.nmstate.io/) - A Declarative API for Host Network Management
- [Netplan](https://netplan.io/) - The network configuration abstraction renderer

*ifstate*'s distinctive feature is to **only** rely on the RTNL protocol (iproute2).


## Status

*ifstate* is in a early development stage, the API and YaML may still change.


## Install & Usage

*ifstate* can be installed using pip:

```
# pip install ifstate
```

## Examples

```yaml
interfaces:
- name: eth0
  kind: physical
  address: 8c:16:45:56:af:cc
- name: eth0.10
  kind: vlan
  link: eth0
  vlan_id: 10
```
