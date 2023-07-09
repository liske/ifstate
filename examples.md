---
title: Examples
---

This is a collection of configuration examples for different interface link types and routing setups.

## Keepalived
- [VRRP with notify_fifo script (recommended)](examples/vrrp-fifo.md)
- [VRRP with notify script](examples/vrrp.md)

## Links
- [Bonding Interface w/ LACP (802.3ad)](examples/lacp.md)
- [EoGRE Layer 2 Tunnel](examples/gretap.md)
- [GENEVE Layer 2 Tunnel](examples/geneve.md)
- [Physical Interface](examples/physical.md)
- [VLAN Subinterface (802.1q)](examples/vlan-dot1q.md)
- [VLAN Q-in-Q Subinterfaces (802.1ad + 802.1q)](examples/vlan-qinq.md)

## VPN
- [WireGuard tunnel](examples/wireguard.md)
- [XFRM Interfaces for multitenant IPsec](examples/xfrm-vrf.md)

## Routing
- [Policy Based Routing (PBR)](examples/pbr.md)
- [Virtual Routing and Forwarding (VRF)](examples/vrf.md)

## Traffic Control
- [simple bandwidth shaping with cshaper](examples/cshaper.md)
- [traffic control shaping](examples/tc-shaping.md)

## XDP/BPF
- [pin a eBPF program for eXpress Data Path (XDP) routing](examples/bpf.md)
- [attach XDP program to interface](examples/xdp.md)

## Misc
- [permanent neighbour/ARP tables entries](examples/neigh.md)
- [ethtool hardware settings](examples/ethtool.md)
- [sysctl interface settings](examples/sysctl.md)
