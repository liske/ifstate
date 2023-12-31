---
title: cshaper
layout: page
permalink: docs/cshaper/
---

[Schema description](../../schema/#cshaper)
 
```yaml
cshaper:
  default:
    # qdisc template for egress traffic
    egress_qdisc:
        kind: cake
        handle: "1:"
    # qdisc template for ingress traffic on ifb link
    ingress_qdisc:
        kind: cake
        handle: "1:"
    # replace pattern to derive the ifb ifname
    ingress_ifname:
        search: ^\D{1,3}
        replace: ifb
```

Examples:
- [simple bandwidth shaping with cshaper](../../examples/cshaper.html)

The *cshaper* feature simplifies the configuration of simple port-based shaper setups based on the CAKE qdisc. The top-level *cshaper* setting is a dictonary of profiles defining CAKE qdisc profiles and a regex to derive the ifb link name.

The default profile should already work for most setups.

[Back](..#configuration-file)

*[CAKE]: Common Applications Kept Enhanced
*[qdisc]: queueing discipline
