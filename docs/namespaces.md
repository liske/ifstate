---
title: namespaces
layout: page
permalink: docs/namespaces/
---

[Schema description](../../schema/#namespaces_pattern1)
 
```yaml
# interfaces in the root netns
interfaces:
- name: enp5s0
  addresses: []
  link:
    state: up
    kind: physical
    permaddr: '54:b2:03:16:94:09'

namespaces:
  tenant1:
    # interfaces in the tenant1 netns
    interfaces:
      # subinterface in vlan 48
      - name: enp5s0.48
        addresses:
          - 192.0.2.1/24
        link:
          kind: vlan
          state: up
          vlan_id: 48
          # link to interface in root netns
          link: enp5s0
          link_netns: null
  tenant2:
    # interfaces in the tenant2 netns
    interfaces:
      # subinterface in vlan 42
      - name: enp5s0.42
        addresses:
          - 192.0.2.1/24
        sysctl:
          mpls:
            input: 0
        link:
          kind: vlan
          state: up
          vlan_id: 42
          # link to interface in root netns
          link: enp5s0
          link_netns: null
```

Exampels:
- [WireGuard tunnel with netns namespace](../../examples/wireguard-netns.html)

The *namespaces* setting allows to configure network namespaces (netns). *IfState* should only be run from the root netns. *IfState* will ignore any netns if the *namespaces* setting is missing in the configuration.

Inside a netns the following settings are possible:
- [interfaces](../interfaces)
- [routing](../routing)
- [options](../options)
- [bpf](../bpf)

If namespaces are used it is possible to bind, link or use a master from another netns (`null` refers to the root netns):

- `master_netns` - use an master interface from another namespace (i.e. a bridge)
- `link_netns` - link the subinterface to an interface in another namespace
- `bind_netns` - bind the outside of a virtual tunnel (wireguard, xfrm, gre, …) in another namespace

All features of *IfState* are netns aware and the link lookup by `businfo` and `permaddr` works across namespaces.

[Back](..#configuration-file)
