---
title: Examples: VLAN Interface (802.1q)
---

# Examples: VLAN Interface (802.1q)

This example configures a VLAN subinterface (IEEE 802.1q):
- rename the base interface to `trunk`
- set the base interface link to `up`
- create a VLAN subinterface for VLAN ID `42`
- set the subinterface link state to `up`
- add an ipv4 address on the subinterface


## ifstate

```yaml
interfaces:
- name: trunk
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up
- name: outside
  addresses:
    - 192.0.2.1/24
  link:
    kind: vlan
    link: eth0
    vlan_id: 42
```


## iproute2

```bash
ip link dev eth0 set down
ip link set dev eth0 name trunk up
ip link add name outside link trunk type vlan id 42
ip link set dev outside up
ip address add 192.0.2.1/24 dev outside
```
