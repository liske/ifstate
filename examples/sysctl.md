# Example: Sysctl interface settings

This example configures sysctl interface settings:
- enable ip forwarding for *all* interfaces
- ignore ipv6 router advertisments by *default*
- accept ipv6 router advertisments on `eth0` and generate a private ipv6 address
- configure a static ipv6 address on `eth1`

[Back](../examples.md)


## ifstate

```yaml
options:
  sysctl:
    all:
      ipv6:
        forwarding: 1
interfaces:
- name: eth0
  link:
    kind: physical
    state: up
  sysctl:
    ipv6:
      accept_ra: 2
      addr_gen_mode: 3
- name: eth1
  addresses:
  - 2001:db8::defa/64
  link:
    kind: physical
    state: up
```


## manual

```bash
sysctl net.ipv6.conf.all.forwarding=1
sysctl net.ipv6.conf.eth0.accept_ra=2
sysctl net.ipv6.conf.eth0.addr_gen_mode=3
ip address add 2001:db8::defa/64 dev eth1
ip link dev eth0 set up
ip link dev eth1 set up
```
