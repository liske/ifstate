---
title: ignore
layout: page
permalink: docs/ignore/
---

[Schema description](../../schema/#ignore)
 
```yaml
ignore:
  ifname:
    - ^eno1$
    - ^wl
```

The *ignore* setting contains a dictionary to configure different items which should be ignored by *IfState* completely:

- [*ipaddr*](../../schema/#ignore_ipaddr) - ip addresses
- [*ipaddr_dynamic*](../../schema/#ignore_ipaddr_dynamic) - dynamic ip addresses (SLAAC)
- [*ifname*](../../schema/#ignore_ifname) - interfaces by name
- [*fdb*](../../schema/#ignore_fdb) - bridge forwarding database entries
- [*routes*](../../schema/#ignore_routes) - routes
- [*rules*](../../schema/#ignore_rules) - PBR rules
- [*netns*](../../schema/#ignore_rules) - netns namespaces

There are also some `*_builtin` entries which contains some sane defaults (i.e. to ignore *docker* bridges or *pppd* interfaces). These built-in entries can be viewed by `ìfstatecli showall`.

[Back](..#configuration-file)

*[PBR]: Policy Based Routing
*[SLAAC]: Stateless Address Autoconfiguration (IPv6)
