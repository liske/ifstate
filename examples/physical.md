# Example: Physical Interface

This example configures an existing physical interface link:
- rename it to `outside`
- add an ipv4 address
- set the link state to `up`

[Back](../examples.md)


## ifstate

```yaml
interfaces:
- name: outside
  addresses:
    - 192.0.2.1/24
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up
```


## iproute2

```bash
ip link dev eth0 set down
ip link set dev eth0 name outside up
ip address add 192.0.2.1/24 dev outside
```
