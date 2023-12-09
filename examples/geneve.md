---
layout: page
---

# Example: GENEVE Layer 2 Tunnel

This example configures a GENEVE layer 2 tunnel and a bridge:
- create a bridge interface `br0`
- create a GENEVE tunnel `gen0` to `192.0.2.2` using VNI `42`
- add `gen0` and the interface `eth0` to the bridge `br0`
- disable STP on the bridge `br0`
- set all interface link states to `up`

[Back](.)


## ifstate

```yaml
interfaces:
- name: br0
  link:
    kind: bridge
    br_stp_state: 0
    state: up
- name: eth0
  link:
    kind: physical
    master: br0
    state: up
- name: gen0
  link:
    kind: geneve
    geneve_id: 42
    geneve_remote: 192.0.2.2
    master: br0
    state: up
```


## manually

```bash
ip link add name br0 type bridge stp_state 0
ip link set dev eth0 master br0
ip link add gen0 type geneve id 42 remote 192.0.2.2
ip link set dev gen0 master br0
ip link dev br0 set up
ip link dev eth0 set up
ip link dev gen0 set up
```
