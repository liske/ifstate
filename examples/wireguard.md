---
layout: page
---

# Example: WireGuard tunnel

This example configures a WireGuard tunnel:
- create a WireGuard interface `wg0`
- set interface link state to `up`
- configure an ip address on `wg0`
- configure the private key from `/etc/wireguard/peer_A.key`
- configure a WireGuard remote peer at `198.51.100.2:4711`
- setup routing for the remote network via `wg0`

[Back](.)


## ifstate

```yaml
interfaces:
- name: wg0
  addresses:
  - 192.0.2.1/25
  link:
    state: up
    kind: wireguard
  wireguard:
    private_key: !include /etc/wireguard/peer_A.key
    peers:
    - public_key: oef+ZSlMWWCF1bEHPaw04TmjPyHKcz2b81njwIQI0xA=
      endpoint: 198.51.100.2:4711
      allowedips:
      - 192.0.2.128/25
routing:
  routes:
  - to: 192.0.2.128/25
    dev: wg0
```


## manually

```bash
ip link add name wg0 type wireguard
ip link set wg0 up
ip address add 192.0.2.1/25 dev wg0
ip route add 192.0.2.128/25 dev wg0
wg set wg0 private-key /etc/wireguard/peer_A.key
wg set wg0 peer oef+ZSlMWWCF1bEHPaw04TmjPyHKcz2b81njwIQI0xA= endpoint 198.51.100.2:4711 allowed-ips 192.0.2.128/25
```
