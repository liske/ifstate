# Example: traffic control shaping

This example configures traffic control settings:
- configure interface eth0 with an ipv4 address
- add traffic control shaping with the [*cake* qdisc](https://man7.org/linux/man-pages/man8/tc-cake.8.html)
- add a `ifb0` device for incoming shaping on eth0
- set shaper to 80Mbps download and 30Mbps upload speed

[Back](../examples.md)


## ifstate

```yaml
interfaces:
- name: ifb0
  link:
    kind: ifb
    state: up
  tc:
    qdisc:
      kind: cake
      bandwidth: 80mbit
- name: eth0
  addresses:
    - 192.0.2.1/24
  link:
    kind: physical
    state: up
  tc:
    qdisc:
      kind: cake
      bandwidth: 30mbit
    filter:
      - kind: matchall
        action:
          - kind: mirred
            direction: egress
            action: redirect
            dev: ifb0
```


## manually

```bash
ip link add name ifb0 type ifb
ip link set ifb0 up
ip address add 192.0.2.1/24 dev eth0
ip link set eth0 up
tc qdisc add dev ifb0 parent root cake bandwidth 80mbit
tc qdisc add dev eth0 parent root cake bandwidth 30mbit
tc filter add dev eth0 matchall action mirred egress redirect dev ifb0
```
