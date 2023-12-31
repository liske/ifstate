---
title: bpf
layout: page
permalink: docs/bpf/
---

[Schema description](../../schema/#bpf)
 
```yaml
bpf:
  # pin BPF program with name `blacklist`
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

Examples:
- [pin a eBPF program for eXpress Data Path (XDP) routing](../../examples/bpf.html)

The *bpf* setting allows to pin BPF programs. The name to the pinning can be later referred from multiple interfaces as XDP BPF program.

[Back](..#configuration-file)

*[BPF]: Berkeley Packet Filter
*[XDP]: eXpress Data Path
