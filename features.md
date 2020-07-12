---
title: Features
---

# Available features

The following features are already available:

- operates idempotent
- basic interfaces settings
  - rename static interfaces by mac address
  - set interface state
- create and configure interfaces
  - supports many [interface types](schema/#interfaces_items_link)
- configure ip addresses
- remove orphan interfaces and ip addresses
- configure routing tables [≥ 0.6.0]
- configure routing rules [≥ 0.7.0]
- configure interface `sysctl` options [≥ 0.7.1]
- configure interface driver and hardware settings via `ethtool` [≥ 0.8.0]
- ignore interfaces by patterns
- ignore ip addresses by prefix lists
- ignore routing table entries by protocol
- ignore routing rules by protocol


# Planned features

The following features a planned for a later release of *ifstate*:

- support for hotplug interfaces
