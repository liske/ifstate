---
title: routing
layout: page
permalink: docs/routing/
---

[Schema description](../../schema/#routing)
 
```yaml
routing:
  # route settings (ip route)
  routes:
    - to: 0.0.0.0/0
      via: 192.0.2.1
  # rule settings (ip rule)
  rules:
    - priority: 42
      iif: eno1
      to: 1.1.1.1/32
      action: prohibit
```

Examples:
- [Policy Based Routing (PBR)](../../examples/pbr.html)
- [Virtual Routing and Forwarding (VRF)](../../examples/vrf.html)

The *routing* setting contains a dictionary to configure routes and PBR rules:

- [*routes*](../../schema/#routing_routes) - routes (`ip route`)
- [*rules*](../../schema/#routing_rules) - PBR rules (`ip rule`)

[Back](..#configuration-file)

*[PBR]: Policy Based Routing
