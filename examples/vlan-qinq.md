# Example: VLAN Q-in-Q Interfaces (802.1ad & 802.1q)

This example configures a service VLAN subinterface (IEEE 802.1ad) with a stacked customer VLAN subinterface (IEEE 802.1q):
- set the base interface link to `up`
- create a S-VLAN subinterface for VLAN ID `10`
- create a C-VLAN subinterface for VLAN ID `42`
- set the subinterface links state to `up`
- add an ipv4 address on the C-VLAN subinterface

[Back](../examples.md)


## ifstate

```yaml
interfaces:
- name: eth0
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up
- name: eth0.10
  addresses: []
  link:
    kind: vlan
    link: eth0
    vlan_id: 10
    vlan_protocol: 802.1ad
- name: eth0.10.42
  addresses:
    - 192.0.2.1/24
  link:
    kind: vlan
    link: eth0.10
    vlan_id: 42
```


## manually

```bash
ip link set dev eth0 up
ip link add name eth0.10 link eth0 type vlan id 10 vlan_protocol 802.1ad
ip link set dev eth0.10 up
ip link add name eth0.10.42 link eth0.10 type vlan id 42
ip link set dev eth0.10.42 up
ip address add 192.0.2.1/24 dev eth0.10.42
```
