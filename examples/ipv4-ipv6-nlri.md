---
layout: page
---

# Example: IPv4 routes via IPv6 next hop NLRI

This example configures an IPv4 route with a next hop which only has an IPv6 address:
- define a virtual interface `loopback` with IPv4 and IPv6 addresses
- configure a physical interface `eth0` with an IPv6 address
- add default IPv4 and IPv6 routes via an IPv6 link-local next hop on `eth0`

[Back](.)


## ifstate

```yaml
interfaces:
- name: loopback
    addresses:
    - 2001:db8::42/128
    - 192.0.2.42/32
    link:
      state: up
      kind: dummy
- name: eth0
  addresses:
    - 2001:db8:0:1000::2/64
  link:
    kind: physical
    state: up
routing:
  routes:
    - to: 0.0.0.0/0
      via: fe80::1
      dev: eth0
    - to: ::/0
      via: fe80::1
      dev: eth0
```

## manually

```bash
# configure loopback
ip link add loopback type dummy
ip link set loopback up
ip address add 2001:db8::42/128 dev loopback
ip address add 192.0.2.42/32 dev loopback

# configure eth0
ip link dev eth0 set up
ip address add 2001:db8:0:1000::2/64 dev eth0

# configure default routes
ip route add ::/0 via fe80::defa dev eth0
ip route add 0/0 via inet6 fe80::defa dev eth0
```
