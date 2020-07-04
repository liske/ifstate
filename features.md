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
  - support many [interface types](schema/#interfaces_items_link)
- configure ip addresses
- remove orphan interfaces and ip addresses
- configure routing tables
- configure routing rules
- ignore interfaces by patterns
- ignore ip addresses by prefix lists
- ignore routing table entries by protocol
- ignore routing rules by protocol


# Planned features

The following features a planned for a later release of *ifstate*:

- interface driver and hardware settings
  - `ethtool`
- configure interface `sysctl` options
- configure `ipset`
- support for hotplug interfaces
