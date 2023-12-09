---
layout: page
---

# Example: Virtual Routing and Forwarding (VRF)

This example attaches two physical interfaces to a [VRF](https://www.kernel.org/doc/Documentation/networking/vrf.txt) called `vrf-blue`:
- configure `eth0` in the default vrf
- create the vrf `vrf-blue`
- add `eth1` and `eth2` to the vrf `vrf-blue`
- configure ip routing

[Back](.)


## ifstate

```yaml
interfaces:
    # default vrf
    - name: eth0
      addresses:
      - 198.51.100.2/31
      link:
        state: up
        kind: physical

    # "blue" vrf
    - name: vrf-blue
      addresses: []
      link:
        state: up
        kind: vrf
        vrf_table: 10

    - name: eth1
      addresses:
      - 192.0.2.2/25
      link:
        state: up
        kind: physical
        master: vrf-blue

    - name: eth2
      addresses:
      - 192.0.2.129/25
      link:
        state: up
        kind: physical
        master: vrf-blue

routing:
    # default route in default vrf
    - to: 0.0.0.0/0
      via: 198.51.100.1

    # default route in "blue" vrf
    - to: 0.0.0.0/0
      via: 192.0.2.1
      table: 10
```


## manually

```bash
ip address add 198.51.100.2/31 dev eth0
ip link dev eth0 set up
ip route add default via 198.51.100.1
ip link add name vrf-blue type vrf table 10
ip link set vrf-blue up
ip link set eth1 master vrf-blue up
ip address add 192.0.2.2/25 dev eth1
ip link set eth2 master vrf-blue up
ip address add 192.0.2.129/25 dev eth2
ip route add default via 192.0.2.1 table 10
```
