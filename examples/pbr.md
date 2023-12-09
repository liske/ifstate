---
layout: page
---

# Example: Policy Based Routing (PBR)

This example configures policy based routing:
- enable ipv4 forwarding via `sysctl`
- rename two interfaces to `inside` and `outside`
- add an ipv4 address for each interface
- configure a default route
- configure policy based routing using another gateway

[Back](.)


## ifstate

```yaml
options:
  sysctl:
    all:
      ipv4:
        forwarding: 1
interfaces:
- name: outside
    addresses:
    - 198.51.100.6/29
    link:
        state: up
        kind: physical
        address: 00:50:56:ad:db:ac
- name: inside
  addresses:
    - 192.0.2.1/24
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up
routing:
  routes:
    - to: 0.0.0.0/0
      via: 198.51.100.1
    - to: 0.0.0.0/0
      via: 198.51.100.2
      table: 100
  rules:
    - priority: 4000
      table: 100
      from: 192.0.2.42
```


## manually

```bash
# enable ipv4 forwarding
sysctl net.ipv4.conf.all.forwarding=1

# configure outside
ip link dev eth0 set down
ip link set dev eth0 name outside up
ip address add 198.51.100.6/29 dev outside

# configure inside
ip link dev eth1 set down
ip link set dev eth1 name inside up
ip address add 192.0.2.1/24 dev inside

# setup routing
ip route add default via 198.51.100.1
ip route add default via 198.51.100.2 table 100
ip rule add from 192.0.2.42 priority 4000 table 100
```
