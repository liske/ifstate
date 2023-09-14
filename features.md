---
title: Features
---

# Available features

The following features are already available:

- operates idempotent
- identify explicit physical interfaces by:
  - permanent mac address (`ethtool -P`) [≥ 1.3.0]
  - bus information (`ethtool -i`) [≥ 1.4.0]
- create and configure interfaces
  - interface state
  - tx queue length [≥ 1.6.0]
  - mtu
  - bridge port settings [≥ 1.7.0]
  - supports many [interface types](schema/#interfaces_items_link)
- configure ip addresses
- remove orphan interfaces and ip addresses
- configure routing tables [≥ 0.6.0]
- configure routing rules [≥ 0.7.0]
- configure interface `sysctl` options [≥ 0.7.1]
- configure interface driver and hardware settings via `ethtool` [≥ 0.7.2]
- full netns namespace support [≥ 1.9.0]
- configure WireGuard settings [≥ 0.8.0]
- load and attach XDP program [≥ 1.6.0]
- configure traffic control (`tc`) qdisc and filters [≥ 1.1.0]
- simple bandwidth shaping using [cake](https://man7.org/linux/man-pages/man8/tc-cake.8.html) (`cshaper`) [≥ 1.5.7]
- conditional interfaces for VRRP failover setups based on keepalived [≥ 1.5.0]
- ignore interfaces by patterns
- ignore ip addresses by prefix lists
- ignore routing table entries by protocol
- ignore routing rules by protocol


# Planned features

The following features a planned for a later release of *ifstate*:

- extend support for traffic control (`tc`)
- support for hotplug interfaces
- XDP maps
- XDP pinning
