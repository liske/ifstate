---
title: CLI
---

# Usage

```bash
usage: ifstatecli [-h] [--version] [-v | -q] [-s] [-c CONFIG]
                  {apply,check,show}

positional arguments:
  {apply,check,show}    specifies the action to perform

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         be more verbose
  -q, --quiet           be more quiet, print only warnings and errors
  -s, --soft-schema     ignore schema validation errors, expect ifstatecli to
                        trigger internal exceptions
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


## show

The `show` action will print a configuration for the running network config. The ouput might be used as a starting point for writing configurations and contains the default ignore settings.

```yaml
# ifstatecli show
ignore:
  ipaddr:
  - fe80::/10
  ipaddr_dynamic: true
  ifname:
  - ^br-[\da-f]{12}
  - ^docker\d+
  - ^lo$
  - ^ppp\d+$
  - ^veth
  - ^virbr\d+
  - ^vrrp\d*\.\d+$
  routes:
  - proto: 1
  - proto: 2
  - proto: 8
  - proto: 9
  - proto: 10
  - proto: 11
  - proto: 12
  - proto: 13
  - proto: 14
  - proto: 15
  - proto: 16
  - proto: 42
  - proto: 186
  - proto: 187
  - proto: 188
  - proto: 189
  - proto: 192
  - to: ff00::/8
  rules:
  - proto: 1
  - proto: 2
  - proto: 8
  - proto: 9
  - proto: 10
  - proto: 11
  - proto: 12
  - proto: 13
  - proto: 14
  - proto: 15
  - proto: 16
  - proto: 42
  - proto: 186
  - proto: 187
  - proto: 188
  - proto: 189
  - proto: 192
interfaces:
- name: eth0
  addresses: []
  link:
    kind: physical
    address: 8c:16:45:3c:f1:42
    state: up
- name: wlan0
  addresses: []
  link:
    kind: physical
    address: 8c:16:54:15:aa:21
    state: down
- name: eth0.10
  addresses:
  - 198.51.100.3/27
  link:
    kind: vlan
    state: up
    vlan_flags:
      state:
        flags: 1
        mask: 4294967295
    vlan_id: 10
    vlan_protocol: 33024
- name: LOOP
  addresses:
  - 192.0.2.3
  - 2001:db8::3
  link:
    kind: dummy
    state: up
routing:
  routes: []
  rules: []
```

You should consider removing any unnecessary options.
