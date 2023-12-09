---
layout: page
---

# Example: ethtool hardware settings

This example configures ethtool hardware settings:
- change auto negotation to 10 or 100Mbps FD
- disable flow control
- add an ipv4 address
- set the link state to `up`

[Back](.)


## ifstate

```yaml
interfaces:
- name: eth0
  addresses:
    - 192.0.2.1/24
  ethtool:
    change:
      autoneg: on
      #  0x002     10baseT Full
      # +0x008    100baseT Full
      advertise: 0x00a
    pause:
      autoneg: on
      tx: off
      rx: off
  link:
    kind: physical
    state: up
```


## manually

```bash
ethtool --pause eth0 autoneg on rx off tx off
ethtool --change eth0 autoneg on adverstise 0x00a
ip address add 192.0.2.1/24 dev eth0
ip link set eth0 up
```
