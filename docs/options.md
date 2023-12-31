---
title: options
layout: page
permalink: docs/options/
---

[Schema description](../../schema/#options)
 
```yaml
options:
  # https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt
  sysctl:
    all:
      # /proc/sys/net/ipv4/conf/all/
      ipv4:
        forwarding: 1
    default:
      # /proc/sys/net/ipv4/conf/default/
      ipv4:
        forwarding: 1

    # /proc/sys/net/mpls/
    # https://www.kernel.org/doc/Documentation/networking/mpls-sysctl.txt
    mpls:
      # set greater 0 to enable mpls forwarding
      platform_labels: 1024
```

Examples:
- [sysctl interface settings](../../examples/sysctl.html)

The *options* setting currently only allows the *sysctl* setting. These network-related sysctl settings are not interface specific.

- [*sysctl.all*](../../schema/#options_sysctl_all) - changes [all interface-specific settings](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)
- [*sysctl.default*](../../schema/#options_sysctl_default) - changes the [interface-specific default settings](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)
- [*sysctl.mpls*](../../schema/#options_sysctl_mpls) - [MPLS settings](https://www.kernel.org/doc/Documentation/networking/mpls-sysctl.txt)

[Back](..#configuration-file)

*[MPLS]: Multiprotocol Label Switching
