---
layout: page
---

# Example: pin a eBPF program for eXpress Data Path (XDP) routing

This example uses XDP:
- load and pin a XDP program from object file
- attach the pinned XDP program to `eth0`
- set interfaces to `up`

[Back](.)


## ifstate

```yaml
bpf:
  blacklist:
    object: /home/thomas/src/xdp-tutorial/basic03-map-counter/xdp_prog_kern.o
    section: xdp

interfaces:
# attach XDP program from pinned BPF program
- name: eth0
  link:
    state: up
    kind: physical
  xdp:
    bpf: blacklist
```

## manually

```bash
mkdfir -p /sys/fs/bpf/ifstate/progs /sys/fs/bpf/ifstate/maps
bpftool prog load /home/thomas/src/xdp-tutorial/basic03-map-counter/xdp_prog_kern.o /sys/fs/bpf/ifstate/progs/blacklist type xdp pinmaps /sys/fs/bpf/ifstate/maps/blacklist
ip link set dev eth0 xdp pinned /sys/fs/bpf/ifstate/progs/blacklist
ip link set dev eth0 up
```
