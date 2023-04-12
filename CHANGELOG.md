# ChangeLog

## 1.8.3 - 2023-04-12

Fixes:
- link: fix broken interface recreation (liske/ifstate#13)
- link: fix unusable tun/tap implementation (liske/ifstate#14)
- link: do not change link states in check mode (liske/ifstate#16)
- link:  fix handling of multiple interface with same mac address (liske/ifstate#18)
- logging: fix using always lastResort logger (liske/ifstate#20)
- vrrp: fix broken fifo instance handling due to extra priority values (liske/ifstate#15)

Changes:
- logging: add syslog logging while running detached (i.e. vrrp script)

## 1.8.2 - 2023-02-17

Changes:
- link: add missing device group support

Fixes:
- link: fix TypeError exception when a physical link is missing (liske/ifstate#8)
- routing: handle unresolvable rt lookups gracefully

**This release fixes a bug that could cause a host to not get a working network configuration at boot time.**

When a physical link is missing ifstate prints a warning about it. Due to
a TypeError exception (liske/ifstate#8) ifstate did crash in the link configuration
phase. This breaks all ip configuration if any referenced physical link
was missing.

## 1.8.1 - 2023-01-30

Changes:
- bpf: add missing map pinning
- bpf: cleanup unused libbpf1 bindings
- bpf: improve error handling
- sysctl: apply settings before interface state is set to up
- xdp: improve error handling

Fixes:
- bpf: do not reload unchanged bpf programs due to broken error condition
- bpf: fix bpffs mount detection
- link: drop IFLA_ALT_IFNAME conflict on IFLA_IFNAME on rename or create
- logging: don't crash if stderr is closed<sup>1</sup> (liske/ifstate#5)
- sysctl: fix setting for renamed interfaces<sup>2</sup>
- sysctl: handle procfs errors gracefully<sup>3</sup> (liske/ifstate#6)
- xdp: fix broken detection of current attached xdp

**This release fixes critical bugs that could cause a host to not get a working network configuration at boot time.**

Remarks:
1) This could break the complete network setup if a host is booted with a broken `console=` kernel parameter.
2) The sysctl settings were applied using the wrong interface name. Combined with 3. it breaks the network setup during boot if the sysctl setting was used on a interface which needs to be renamed.
3) Do not crash if a procfs file cannot be opened.

## 1.8.0 - 2022-11-17

Changes:
- brport: add settings to show commands
- bpf: add shared bpf programs support
- shell: add tab completion
- xdp: pin maps for loaded objects

Fixes:
- xdp: fix error handling on libbpf.bpf_object__open_file
- xdp: fix loading of pinned programs

## 1.7.0 - 2022-11-13

Changes:
- bport: add support for bridge port settings
- logger: silence skipped steps unless being verbose
- shell: add a interactive python shell

Fixes:
- link: fix exception on link recreation
- link: several minor bugfixes

## 1.6.1 - 2021-11-05

Changes:
- xdp: allow to specify attach mode
- xdp: check libbpf symbols before enabling feature

Fixes:
- schema: fix xdp pinned format pattern
- xdp: fix exception if libbpf.so.1 is not available

## 1.6.0 - 2021-11-03

Changes:
- xdp: add experimental eXpress Data Path (XDP) support
- link: add txqlen link setting

Fixes:
- schema: fix link kind descriptions

## 1.5.8 - 2021-11-14

Changes:
- neighbours: add static ip neighbour configuration

Fixes:
- schema: revert to json schema Draft 7 due to regressions
- schema: fix usage of ipv4 & ipv6 format
- packaging: make setup.py work with pyroute2<0.6, pyroute2>=0.6 and
             pyroute2.minimal

## 1.5.7 - 2021-10-31

Changes:
- cshaper: add simple tc-cake based shaping

Fixes:
- addresses: add missing exception handling
- pyroute2: workaround NetlinkError regression (pyroute2 #845 #847)

## 1.5.6 - 2021-09-25

Changes:
- link: add attribute value mappings for bond and vlan interfaces
- schema: add link name validation

Fixes:
- link: fix exception while 'show' for master/link to other netns
- schema: simplify and make it work on jschon validator
- schema: fix shortened path output on validation errors

## 1.5.5 - 2021-08-25

Fixes:
- ethtool: fix module import for pyroute2 0.6+
- show: fix missing attributes
- tc: fix internal exception during apply

## 1.5.4 - 2021-08-01

Fixes:
- link: recreate virtual interfaces if updating fails
- wireguard: deep compare a peer's set of allowedips

## 1.5.3 - 2021-07-05

Fixes:
- schema: fix broken geneve links

## 1.5.2 - 2021-06-05

Changes:
- routing: make route matching verbose in verbose mode

Fixes:
- routing: fix ipv6 routes get removed accidentally since the kernel uses
           a default priority of 1024 vs. 0 on ipv4 routes

## 1.5.1 - 2021-03-15

Fixes:
- check: fix broken check command (TypeError exception)

## 1.5.0 - 2021-03-23

Changes:
- vrrp: add support for failover link setups, design to work with
        keepalived's notify script or fifo interface
- ignore: add proto keepalived(18) to builtin lists

Fixes:
- addresses: replacing primary ipv4 addr was broken due to add-before-del
- link: make businfo available in iface settings check
- link: make businfo lower case
- link: supress exceptions on unsupported permaddr or businfo
- wireguard: fix broken apply iface settings

## 1.4.0 - 2021-01-09

Changes:
- support bus_info link identification [ethtool -i]

## 1.3.2 - 2020-12-20

Fixes:
- wireguard: fix name of persistent_keepalive_interval
- link: add permaddr to kernel iface settings before for compare

## 1.3.1 - 2020-12-07

Fixes:
- several bugs in show command:
  - show missing master device
  - ignore non-scalar link attributes
  - fix kind None for some physical devices

## 1.3.0 - 2020-09-28

Changes:
- support prefered src address on routes
- support preference on routes
- support mtu setting on links
- support permanent address link identification [ethtool -P]
- improve show command output, drop unset values
- apply builtin filters on show command
- add the showall command to view builtin settings

Fixes:
- fix broken show command

## 1.2.1 - 2020-09-25

Changes:
- add schema support for ifalias

Fixes:
- fix link lookup by mac address

## 1.2.0 - 2020-09-18

Changes:
- ignore: move defaults to builtin keys to make them
  extendable by the config
- update project & schema url to new domain (ifstate.net)
- improve tc implementation, support ingress qdisc

Fixes:
- handle empty configs more gracefully
- add quirks to make veth links work

## 1.1.0 - 2020-09-04

Changes:
- link: add ifb support
- tc: add experimental support
  - tc qdisc
  - tc filter
- wireguard: catch exception if wireguard netlink support is missing

## 1.0.0 - 2020-08-24

Changes:
- ignore dynamic ip addresses by default and make it configurable
- logging: make it async to prevent lockup while running ifstatecli from remote connections
- netlink: handle exceptions more gracefully (`EEXIST`)
- parser: handle pyyaml exceptions more gracefully
- parser: improve `!include` tag
- schema: add missing additionalProperties constraints
- schema: add missing `master` link property (for dummy and wireguard links)
- schema: add `--soft-schema` CLI parameter

## 0.9.0 - 2020-08-17

Changes:
- ignore keepalive's vrrp interfaces by default
- make routing ignores more flexible allowing to filter for any properties
- jsonschema: do not allow addtional properties on more settings
- handle missing physical links more gracefully
- ethtool: fallback to predefined executable if it is not found in `$PATH`
- rules: make table id only required for `to_tbl` action
- multiple bugfixes


## 0.8.1 - 2020-07-26

Changes:
- Add missing `dummy` interface type to schema.
- Fix WireGuard peer `endpoint` setting handling.


## 0.8.0 - 2020-07-26

Changes:
- ifstatecli: Add `!include` tag to read secrets from external files.
- Add WireGuard configuration support.


## 0.7.3 - 2020-07-24

Changes:
- Fix broken ethtool pause schema.
- Make link dependencies work.
- Change interface state in a final dedicated step.
- Minor bugfixes.


## 0.7.2 - 2020-07-16

Changes:
- Add ethtool support.
- Minor cleanups.

## 0.7.1 - 2020-07-12

Changes:
- Add *sysctl* support.
- Add more exception handling for *pyroute2* calls (NetLinkErrors).
- Minor bugfixes.


## 0.7.0 - 2020-07-04

Changes:
- Ignore kernel routes flagged `RTM_F_CLONED`.
- Ignore IPv6 multicast route prefix (required for `VRF`).
- Merge `ignore` configuration for unset keys with default values.
- Handle interface name collisions more gracefully.
- Implement routing rule support.


## 0.6.3 - 2020-06-20

Changes:
- Add interface index translations for some interface types:
  - `GRE`
  - `IP6GRE`
  - `VXLAN`
  - `XFRM`
- Delay route interface lookup to fix exception for routes on new interfaces.


## 0.6.2 - 2020-06-16

Changes:
- Bugfix: support `master` attribute as interface name (add lookup).
- Improve route comparision: ignore unconfigured kernel route settings.
- Update schema to support integer values for various fields.


## 0.6.1 (first public release) - 2020-06-09

Changes:
- Add schema support (json-schema).
- Ignore dynamic docker bridges by default (`^br-[\da-f]{12}`).
