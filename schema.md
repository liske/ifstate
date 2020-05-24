---
title: Schema
---

# YaML

The YaML configuration file for *ifstatecli* uses a loose schema with the following top-level keys:

```yaml
options:
    # ...
ignore:
    # ...
interfaces:
    # ...
```

## options

Global settings are defined in the `options` key.


## ignore

Ignore patterns for links and ip addresses are defined in the `ignore` key.

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

Configures ip addresses (`ip address`) of the interface.

### link

Configures link settings (`ip link`) of the interface.
