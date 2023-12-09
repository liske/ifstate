---
layout: page
---

# Example: WireGuard tunnel with netns namespace

This example configures a WireGuard tunnel for a branch office using netns namespace isolation:
- configures an uplink interface in a dedicated outside netns namespace
- create a WireGuard interface `wg0` in the root netns namespace while the encrypted traffic originates from the outside netns namespace
- configure routing in both netns namespaces

[Back](.)


## ifstate

```yaml
interfaces:
# inside interface
- name: eth0
  addresses:
  - 192.0.2.129/25
  link:
    state: up
    kind: physical
# wireguard vpn
- name: wg0
  addresses:
  - 192.0.2.1/25
  link:
    state: up
    kind: wireguard
    bind_netns: outside
  wireguard:
    private_key: !include /etc/wireguard/peer_A.key
    peers:
    - public_key: oef+ZSlMWWCF1bEHPaw04TmjPyHKcz2b81njwIQI0xA=
      endpoint: 198.51.100.2:4711
      allowedips:
      - 0.0.0.0/0

routing:
  rules: []
  routes:
  # default route via vpn
  - to: 0.0.0.0/0
    dev: wg0

namespaces:
  outside:
    interfaces:
    - name: eth0
      addresses:
      - 198.51.100.2/31
      link:
        state: up
        kind: physical
    routing:
      rules: []
      routes:
      - to: 0.0.0.0/0
        via: 198.51.100.1
```
