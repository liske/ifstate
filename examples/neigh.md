---
layout: page
---

# Example: permanent neighbour/ARP tables entries

This example configures an neighbour entry on a physical link:
- add an ipv4 and address
- set the link state to `up`
- add static ARP entry

[Back](.)


## ifstate

```yaml
interfaces:
- name: eth0
  addresses:
    - 192.0.2.1/24
  link:
    kind: physical
    state: up
  neighbours:
    192.0.2.42: 42:00:00:00:de:fa
```


## manually

```bash
ip address add 192.0.2.1/24 dev eth0
ip link dev eth0 set up
ip neigh add 192.0.2.42 lladdr 42:00:00:00:de:fa dev eth0 nud permanent
```
