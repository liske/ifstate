---
title: Schema
---

# YaML

The YaML configuration file for *ifstatecli* uses a loose schema with the following top-level keys:

```yaml
options:
    # global options
ignore:
    # ignore patterns
interfaces:
    # interfaces and ip addresses
routing:
    # routing tables and rules
```

## options

Global settings are defined in the `options` key.


## ignore

Ignore patterns defined in the `ignore` key are used to skip interface, ip address or routing objects.

```yaml
# ...
ignore:
    ipaddr:
    - fe80::/10
    ifname:
    - ^docker\d+
    - ^lo$
    - ^ppp\d+$
    - ^veth
    - ^virbr\d+
    routes:
# ...
```
### ipaddr

A list of ip prefixes. Ip addresses matching one of this prefixes are ignored and will not be removed. It might be a valid idea to ignore link-local addresses.

### ifname

A list of regex patterns. Interface names matching those names are ignored and will not be removed. It should always ignore at least `lo`.


## interfaces

A list of interface settings. Each entry requires a `name` key.

```yaml
# ...
interfaces:
    - name: eth0.10
      addresses:
      - 198.51.100.3/27
      link:
        kind: vlan
        link: eth0
# ...
```

### addresses

Configures ip addresses ([`ip address`](https://man7.org/linux/man-pages/man8/ip-address.8.html)) of the interface.

### link

Configures link settings ([`ip link`](https://man7.org/linux/man-pages/man8/ip-link.8.html)) of the interface.


## routing

Configures routing rules and tables.

### routes

A list of routing table entries ([`ip route`](https://man7.org/linux/man-pages/man8/ip-route.8.html)) to be configured. Each entry requires at least a `to` key.

```yaml
# ...
routing:
    routes:
    - to: 198.51.100.128/25
      via: 198.51.100.1
# ...
```
