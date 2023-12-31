---
title: vrrp
layout: page
permalink: docs/vrrp/
---

[Schema description](../../schema/#interfaces_items_vrrp)
 
```yaml
# …

interfaces:
# …
- name: vip
  addresses:
  # the VRRP ip
  - 192.0.2.254/24
  link:
    # any interface can be used as a vrrp interface
    kind: macvlan
    state: up
    # virtual interfaces use random mac addresses,
    # consider to set it to a static value
    address: 42:0d:ef:a0:00:21
    link: eth0
  # configure this interface only in vrrp(-fifo) mode
  # (DRY: add a YAML anchor)
  vrrp: &vrrp0
    # match a Keepalived's instance by name
    name: VRRP0
    type: instance
    # enable interface/add route only in these states
    states:
    - master

# …

routing:
  routes:
    - to: 0.0.0.0/0
      via: 192.0.2.1
      # configure the default route only in vrrp(-fifo) mode
      # (DRY: refer to YAML anchor)
      vrrp: *vrrp0

# …
```

Examples:
- [VRRP with notify_fifo script (prefered)](../../examples/vrrp-fifo.html)
- [VRRP with notify script](../../examples/vrrp.html)

*IfState* can be combined with [*Keepalived*](https://www.keepalived.org/) as a notify script for complex network HA setups. Interfaces, routes and routing rules with a *vrrp* option will only be handled by `ifstatecli vrrp-fifo` (recommended) or `ifstatecli vrrp`.

Example for a basic `/etc/keepalived/keepalived.conf`:

```python
global_defs {
  # script settings
  script_user root
  enable_script_security

  # vrrp notify fifo (ifstate)
  vrrp_notify_fifo /run/vrrp-ifstate.fifo
  vrrp_notify_fifo_script "/usr/bin/ifstatecli vrrp-fifo"
}

vrrp_instance VRRP0 {
  # VRRP interface
  interface eth0

  # VRRP w/o VIP (requires keepalived 2.2.8+)
  no_virtual_ipaddress

  # VRRP router id
  virtual_router_id 21

  # instance priority
  priority 100

  # …
}
```

This allows to build active/standby HA gateways where only a single ip address for each interface is required. The vrrp protocol of *Keepalived* can be run on a dedicated link or using ipv6 link-local addresses, only. This allows to keep the kernels reverse path filtering (`/proc/sys/net/ipv4/conf/*/rp_filter` or `rpfilter` netfilter module) enabled in strict mode.

[Back](..#vrrp-actions--keepalived)

*[PBR]: Policy Based Routing
