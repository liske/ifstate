---
title: Features
---

# Available features

The following features are already available:

- operates idempotent
- basic interfaces settings
- identify explicit physical interfaces by:
  - permanent mac address (`ethtool -P`) [≥ 1.3.0]
  - bus information (`ethtool -i`) [≥ 1.4.0]
- create and configure interfaces
  - supports many [interface types](schema/#interfaces_items_link)
- configure ip addresses
- remove orphan interfaces and ip addresses
- configure routing tables [≥ 0.6.0]
- configure routing rules [≥ 0.7.0]
- configure interface `sysctl` options [≥ 0.7.1]
- configure interface driver and hardware settings via `ethtool` [≥ 0.7.2]
- configure WireGuard settings [≥ 0.8.0]
- configure traffic control (`tc`) qdisc and filters [≥ 1.1.0]
- cshaper: simple traffic control (`tc`) for cake based traffic shaping [≥ 1.5.7]
- conditional interfaces for VRRP failover setups based on keepalived [≥ 1.5.0]
- ignore interfaces by patterns
- ignore ip addresses by prefix lists
- ignore routing table entries by protocol
- ignore routing rules by protocol


# Planned features

The following features a planned for a later release of *ifstate*:

- extend support for traffic control (`tc`)
- support for hotplug interfaces
