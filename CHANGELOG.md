# ChangeLog

## 1.5.2

Fixes:
- routing: fix ipv6 route default priority from 0 to 1024

## 1.5.1

Fixes:
- check: fix broken check command (TypeError exception)

## 1.5.0

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

## 1.4.0

Changes:
- support bus_info link identification [ethtool -i]

## 1.3.2

Fixes:
- wireguard: fix name of persistent_keepalive_interval
- link: add permaddr to kernel iface settings before for compare

## 1.3.1

Fixes:
- several bugs in show command:
  - show missing master device
  - ignore non-scalar link attributes
  - fix kind None for some physical devices

## 1.3.0

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

## 1.2.1

Changes:
- add schema support for ifalias

Fixes:
- fix link lookup by mac address

## 1.2.0

Changes:
- ignore: move defaults to builtin keys to make them
  extendable by the config
- update project & schema url to new domain (ifstate.net)
- improve tc implementation, support ingress qdisc

Fixes:
- handle empty configs more gracefully
- add quirks to make veth links work

## 1.1.0

Changes:
- link: add ifb support
- tc: add experimental support
  - tc qdisc
  - tc filter
- wireguard: catch exception if wireguard netlink support is missing

## 1.0.0

Changes:
- ignore dynamic ip addresses by default and make it configurable
- logging: make it async to prevent lockup while running ifstatecli from remote connections
- netlink: handle exceptions more gracefully (`EEXIST`)
- parser: handle pyyaml exceptions more gracefully
- parser: improve `!include` tag
- schema: add missing additionalProperties constraints
- schema: add missing `master` link property (for dummy and wireguard links)
- schema: add `--soft-schema` CLI parameter

## 0.9.0

Changes:
- ignore keepalive's vrrp interfaces by default
- make routing ignores more flexible allowing to filter for any properties
- jsonschema: do not allow addtional properties on more settings
- handle missing physical links more gracefully
- ethtool: fallback to predefined executable if it is not found in `$PATH`
- rules: make table id only required for `to_tbl` action
- multiple bugfixes


## 0.8.1

Changes:
- Add missing `dummy` interface type to schema.
- Fix WireGuard peer `endpoint` setting handling.


## 0.8.0

Changes:
- ifstatecli: Add `!include` tag to read secrets from external files.
- Add WireGuard configuration support.


## 0.7.3

Changes:
- Fix broken ethtool pause schema.
- Make link dependencies work.
- Change interface state in a final dedicated step.
- Minor bugfixes.


## 0.7.2

Changes:
- Add ethtool support.
- Minor cleanups.

## 0.7.1

Changes:
- Add *sysctl* support.
- Add more exception handling for *pyroute2* calls (NetLinkErrors).
- Minor bugfixes.


## 0.7.0

Changes:
- Ignore kernel routes flagged `RTM_F_CLONED`.
- Ignore IPv6 multicast route prefix (required for `VRF`).
- Merge `ignore` configuration for unset keys with default values.
- Handle interface name collisions more gracefully.
- Implement routing rule support.


## 0.6.3

Changes:
- Add interface index translations for some interface types:
  - `GRE`
  - `IP6GRE`
  - `VXLAN`
  - `XFRM`
- Delay route interface lookup to fix exception for routes on new interfaces.


## 0.6.2

Changes:
- Bugfix: support `master` attribute as interface name (add lookup).
- Improve route comparision: ignore unconfigured kernel route settings.
- Update schema to support integer values for various fields.


## 0.6.1 (first public release)

Changes:
- Add schema support (json-schema).
- Ignore dynamic docker bridges by default (`^br-[\da-f]{12}`).
