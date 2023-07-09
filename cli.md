---
title: CLI
---

# Usage

```bash
usage: ifstatecli [-h] [--version] [-v | -q] [-s] [-c CONFIG] {apply,check,shell,show,showall,vrrp,vrrp-fifo} ...

positional arguments:
  {apply,check,shell,show,showall,vrrp,vrrp-fifo}
                        specifies the action to perform
    apply               update the network config
    check               dry run update the network config
    shell               launch interactive python shell (pyroute2)
    show                show running network config
    showall             show running network config (more settings)
    vrrp                run as keepalived notify script
    vrrp-fifo           run as keepalived notify_fifo_script

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         be more verbose
  -q, --quiet           be more quiet, print only warnings and errors
  -s, --soft-schema     ignore schema validation errors, expect ifstatecli to trigger internal exceptions
  -c CONFIG, --config CONFIG
                        configuration YaML filename
```

# Actions

## apply

The *apply* action will reconfigure the network config of the host to match the state of the config file:

```bash
# ifstatecli apply
configuring interface links
 eth0            ok
 eth0.10         add
 wlan0           change
 LOOP            ok
 eth1            orphan
 eth1.20         del

configuring ip addresses...
 eth0.10         198.51.100.3/27
 LOOP            192.0.2.3/32
 LOOP            2001:db8::3/128
```

## check

The *check* action will parse the config file and does a **dry run** of the *apply* action.


## shell

*For advanced users!*

The `shell` action starts a interactive python shell with a pyroute2 object (symbol `ìpr`). To get highlighting in `pprint` you need to install the `Pygments` python module.

```shell
# ifstatecli shell
Links:
   1: lo
   2: eth0
   3: eth1
   4: eth2
   5: eth3

Symbols:
  ipr = pyroute2.IPRoute()

ifstate 1.8.5; pyroute2 0.7.8
>>> pprint(ipr.get_links(1)[0])
```


## show

The `show` action will print a configuration for the running network config. The ouput might be used as a starting point for writing configurations.

```yaml
# ifstatecli show
interfaces:
- name: eth0
  addresses: []
  link:
    kind: physical
    address: 8c:16:45:3c:f1:42
    businfo: 0000:00:1f.6
    state: up
- name: wlan0
  addresses: []
  link:
    kind: physical
    address: 8c:16:54:15:aa:21
    businfo: 0000:05:00.0
    state: down
- name: eth0.10
  addresses:
  - 198.51.100.3/27
  link:
    kind: vlan
    state: up
    vlan_protocol: 802.1q
    vlan_id: 10
    link: eth0

- name: LOOP
  addresses:
  - 192.0.2.3
  - 2001:db8::3
  link:
    kind: dummy
    state: up
routing:
  routes:
  - to: 0.0.0.0/0
    table: main
    dev: eno1
```

You should consider removing any unnecessary options.

## showall

The `showall` action will print a configuration for the running network config
including internal default settings from the `ignore` section.


## vrrp

The `vrrp` action can be used to run ifstate as a notify script from *keepalived*. If possible it is recommended to use the `vrrp-fifo` action as notify_fifo script.

[More…](examples.md#keepalived)

## vrrp-fifo

The `vrrp-fifo` action can be used to run ifstate as a notify_fifo script from *keepalived*.

[More…](examples.md#keepalived)
