---
layout: page
---

# Example: attach eXpress Data Path (XDP) program to interface

This example uses XDP:
- set interface links to `up`
- load a XDP program from object file and attach it to `eth0`
- clear any attached XDP program from `eth1`

[Back](.)


## ifstate

```yaml
interfaces:

# attach XDP program from file
- name: eth0
  link:
    state: up
    kind: physical
  xdp:
    object: /home/thomas/src/xdp-tutorial/basic01-xdp-pass/xdp_pass_kern.o
    section: xdp

# clear attached XDP program
- name: eth1
  link:
    state: up
    kind: physical
  xdp: no
```

## manually

```bash
ip link set dev eth0 up
ip link set dev enp0s31f6 xdp object /home/thomas/src/xdp-tutorial/basic01-xdp-pass/xdp_pass_kern.o section xdp

ip link set dev eth1 up
ip link set dev eth1 xdp off
```
