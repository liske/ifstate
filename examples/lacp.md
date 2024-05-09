---
layout: page
---

# Example: Bonding Interface w/ LACP (802.3ad)

This example configures a bond interface with two physical interfaces using LACP (IEEE 802.3ad) with fast timers:
- create a bond interface `bond0`
- add an ipv4 address to `bond0`
- assign phyiscal interfaces to `bond0`
- set the physical interfaces links to `up`

[Back](.)


## ifstate

```yaml
interfaces:
# bonding interface
- name: bond0
  addresses:
  - 192.0.2.1/24
  link:
    state: up
    kind: bond
    # 802.3ad
    bond_mode: 4
    bond_ad_lacp_rate: 1
    # layer3+4
    bond_xmit_hash_policy: 1
    bond_miimon: 100
    bond_updelay: 300
# first physical interface
- name: port1
  addresses: []
  link:
    state: up
    kind: physical
    businfo: '0000:03:00.0'
    master: bond0
# second physical interface
- name: port2
  addresses: []
  link:
    state: up
    kind: physical
    businfo: '0000:03:00.1'
    master: bond0
```


## manually

```bash
# bonding interface
ip link add name bond0 bond lacp_rate 1 miimon 100 mode 802.3ad xmit_hash_policy layer3+4 updelay 300
ip link set bond0 up
ip address add 192.0.2.1/24 dev bond0
# first physical interface
ip link set dev eth0 name port1 up
ip link set dev port1 master bond0
ip link set dev port1 up
# second physical interface
ip link set dev eth1 name port2 up
ip link set dev port2 master bond0
ip link set dev port2 up
```
