---
title: Examples
layout: page
permalink: examples/
---

This is a collection of configuration examples for different interface link types and routing setups.

## Keepalived
- [VRRP with notify_fifo script (prefered)](vrrp-fifo.html)
- [VRRP with notify script](vrrp.html)

## Links
- [Bonding Interface w/ LACP (802.3ad)](lacp.html)
- [EoGRE Layer 2 Tunnel](gretap.html)
- [GENEVE Layer 2 Tunnel](geneve.html)
- [Physical Interface](physical.html)
- [VLAN Subinterface (802.1q)](vlan-dot1q.html)
- [VLAN Q-in-Q Subinterfaces (802.1ad + 802.1q)](vlan-qinq.html)

## VPN
- [WireGuard tunnel](wireguard.html)
- [WireGuard tunnel with netns namespace](wireguard-netns.html)
- [XFRM interfaces with VRF-based multitenant IPsec](xfrm-vrf.html)

## Routing
- [Policy Based Routing (PBR)](pbr.html)
- [Virtual Routing and Forwarding (VRF)](vrf.html)

## Traffic Control
- [simple bandwidth shaping with cshaper](cshaper.html)
- [traffic control shaping](tc-shaping.html)

## XDP/BPF
- [pin a eBPF program for eXpress Data Path (XDP) routing](bpf.html)
- [attach XDP program to interface](xdp.html)

## Misc
- [permanent neighbour/ARP tables entries](neigh.html)
- [ethtool hardware settings](ethtool.html)
- [sysctl interface settings](sysctl.html)
