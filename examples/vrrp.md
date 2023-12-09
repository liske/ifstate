# Example: VRRP with keepalived's notify script

This basic example uses keepalived for VRRP and ifstate as vrrp_fifo script:
- use keepalived for VRRP
- use ifstate as notify script to configure the floating virtual IP

*Keepalived recommends to use [notify_fifo](vrrp-fifo.md) over notify scripts! The fifo is more efficient (keepalived + ifstate) and prevents race conditions as no notify scripts run in parallel.*

[Back](../examples.md)


## ifstate

```yaml
interfaces:
  # used as fail-over switch for all VRRP instances
  - name: HA
    addresses: []
    link:
      kind: dummy
      state: up

  # used for soft-fail-over a single VRRP instance
  # (after boot the interface is intentionally down)
  - name: HA-VIP1
    addresses: []
    link:
      kind: dummy

  # physical interface used for VRRP
  - name: eth0
    addresses:
      - 192.0.2.2/29
    link:
      state: up
      kind: physical
      businfo: "0000:10:00.3"

  # virtual interface for the VIP
  - name: VIP1
    addresses:
      - 192.0.2.1/29
    link:
      kind: macvlan
      state: up
      address: 42:0d:ef:a0:00:21
      link: eth0
    vrrp:
      name: VIP1
      type: instance
      states:
      - master
```

## keepalived

The following example `keepalived.conf` only contains a minimalistic setup, you should consider more VRRP related tuning (VRRP version, timers, multicast vs. unicast mode, …).

```python
global_defs {
  # script settings
  script_user root
  enable_script_security
}

vrrp_instance VIP1 {
  # start-up default state
  state BACKUP

  # VRRP interface
  interface eth0

  # VRRP w/o VIP (requires keepalived 2.2.8+)
  no_virtual_ipaddress

  # VRRP state depending on other interfaces
  track_interface {
    HA
    HA-VIP1 weight 20
  }

  # VRRP router id
  virtual_router_id 21

  # instance priority
  priority 100

  # preemption delay
  preempt_delay 30

  # vrrp notify fifo (ifstate)
  notify "/usr/bin/ifstatecli vrrp"
}
```