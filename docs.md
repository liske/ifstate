---
title: Docs
layout: page
permalink: docs/
---

# Declarative network stack configuration

*IfState* will (re)configure the hosts network stack configuration to match the desired configuration. As a result unspecified interfaces or ip addresses are automatically shutdown or removed. It should always be possible to achieve the desired network configuration from any (complex) previous state. Simular to *ansible* only those parts of the network stack that are referenced in the configuration file are taken into account.

# Usage

On [Alpine Linux](https://www.alpinelinux.org) *IfState* can be installed via *apk* and is packaged with a init script. *IfState* provides the CLI command `ifstatecli` as an interface.

- [installing IfState](install)
- [ifstatecli usage](cli)

# Configuration file

*IfState* uses a YaML configuration file which needs to comply with the [*IfState Configuration Schema*](../schema). The default filename of the config file is `/etc/ifstate/config.yml`.

This is a basic example configuration for a single interface and a default route:
```yaml
# yaml-language-server: $schema=https://ifstate.net/schema/ifstate.conf.schema.json

## default/implicit interface settings (optional)
# defaults: ...

## global sysctl options (optional)
# options: ...

## ignore settings to ignore existing interface, ip addresses, ... (optional)
# ignore: ...

## load and pin bpf programs (optional)
# bpf: ...

## "cake shaper" templates (optional)
# cshaper: ...

## interface configuration block (required)
interfaces:
- name: eno1
  addresses:
  - 192.0.1.254/24
  link:
    state: up
    kind: physical
    businfo: 0000:00:1f.6

## routing settings (optional)
routing:
  routes:
  - to: 0.0.0.0/0
    via: 192.0.2.1
  rules: []

## configuration for netns namespaces (optional)
# namespaces: ...
```

Top-level setttings of the configuration file:
- [interfaces](interfaces)
- [routing](routing)
- [ignore](ignore)
- [options](options)
- [defaults](defaults)
- [cshaper](cshaper)
- [namespaces](namespaces)
- [bpf](bpf)

The [JSON schema of the configuration file](../schema) is available in the [JSON Schema Store](https://www.schemastore.org/json/) (as `ifstate.conf`). Most modern editors and IDEs have native support for JSON Schema Store.

Adding the following line to the configuration file instructs editors and IDEs using the [YAML Language Server](https://github.com/redhat-developer/yaml-language-server#clients) to load the *IfState* schema automatically:

```yaml
# yaml-language-server: $schema=https://ifstate.net/schema/ifstate.conf.schema.json
```


# VRRP actions & Keepalived

*IfState* can be combined with [*Keepalived*](https://www.keepalived.org/) as a notify script. The [vrrp option](vrrp.html) for interface and routing settings allows to reconfigure parts of the network stack depending on the state of a VRRP instance or group. This allows to move complex network configuration out of *Keepalived* while still using it for VRRP.
