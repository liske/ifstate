---
title: interfaces
layout: page
permalink: docs/interfaces/
---

[Schema description](../../schema/#interfaces)
 
```yaml
interfaces:
# list of interface settings
- name: eno1
  # ip addresses (ip address)
  addresses:
  - 192.0.1.254/24
  # link settings (ip link)
  link:
    state: up
    kind: physical
    businfo: 0000:00:1f.6
```

Examples:
- [Bonding Interface w/ LACP (802.3ad)](../../examples/lacp.html)
- [EoGRE Layer 2 Tunnel](../../examples/gretap.html)
- [GENEVE Layer 2 Tunnel](../../examples/geneve.html)
- [Physical Interface](../../examples/physical.html)
- [VLAN Subinterface (802.1q)](../../examples/vlan-dot1q.html)
- [VLAN Q-in-Q Subinterfaces (802.1ad + 802.1q)](../../examples/vlan-qinq.html)

The *interfaces* setting contains a list of settings for network interfaces. Each interface needs at least have an uniqure interface name.

The *link* setting defines the type and states of the interfaces. In contrast to virtual interfaces, physical interfaces cannot be created or destroyed. It is therefore important that physical interfaces can be uniquely identified. *IfState* provides the following properties to uniquely identify an interface (in order of priority):

1. `link.businfo` - the PCI or USB bus address
2. `link.permaddr` - the built-in permanent mac address
3. `link.address` - the mac address
4. `name` - the interface name

The properties *businfo* and *permaddr* cannot be changed in Linux and are therefore the most reliable identifiers.

Other settings available for an inteface:

- [*addresses*](../../schema/#interfaces_items_addresses) - assigned ip addresses
- [*brport*](../../schema/#interfaces_items_brport) - bridge port specific settings
- [*fdb*](../../schema/#interfaces_items_fdb) - permanent bridge forwarding database entries
- [*vrrp*](../../schema/#interfaces_items_vrrp) - VRRP action conditions
- [*link*](../../schema/#interfaces_items_link) - link settings
- [*neighbours*](../../schema/#interfaces_items_neighbours) - permanent ip neighbour cache entries
- [*sysctl*](../../schema/#interfaces_items_sysctl) - interface specific procfs settings
- [*ethtool*](../../schema/#interfaces_items_ethtool) - ethtool settings
- [*cshaper*](../../schema/#interfaces_items_cshaper) - simplified tc settings ("cake shaper")
- [*tc*](../../schema/#interfaces_items_tc) - traffic control settings
- [*wireguard*](../../schema/#interfaces_items_wireguard) - wireguard configuration and peers
- [*xdp*](../../schema/#interfaces_items_xdp) - assign eXpress Data Path BPF programs

[Back](..#configuration-file)
