---
layout: page
---

# Example: EoGRE Layer 2 Tunnel

This example configures a Ethernet-over-GRE layer 2 tunnel and a bridge:
- create a bridge interface `br0`
- create a EoGRE tunnel `eogre` to `192.0.2.2` using VNI `42`
- add `eogre` and the interface `eth0` to the bridge `br0`
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
- name: eogre
  link:
    kind: gretap
    gre_local: 192.0.2.1
    gre_remote: 192.0.2.2
    master: br0
    state: up
```


## manually

```bash
ip link add name br0 type bridge stp_state 0
ip link set dev eth0 master br0
ip link add eogre type gretap local 192.0.2.1 remote 192.0.2.2
ip link set dev eogre master br0
ip link set dev br0 up
ip link set dev eth0 up
ip link set dev eogre up
```
