---
title: Examples: Physical Link
---

This example configures an existing physical link.


# ifstate

```yaml
interfaces:
- name: eth0
  addresses:
    - 192.0.2.1/24
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up
```


# iproute2

```bash
ip link dev eth0 set up
ip address replace 192.0.2.1/24 dev eth0
```
