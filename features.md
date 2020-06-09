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
  - support many [interface types](schema/#interfaces_items_link_kind)
- configure ip addresses
- remove orphan interfaces and ip addresses
- configure routing tables
- ignore interfaces by patterns
- ignore ip addresses by prefix lists
- ignore routing table entries by protocol


# Planned features

The following features a planned for a later release of *ifstate*:

- configure ip routing rules
  - `ip rules`
- interface driver and hardware settings
  - `ethtool`
- support for hotplug interfaces
- configure `ipset`
