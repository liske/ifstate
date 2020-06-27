---
title: [Examples](../examples.md)
---

# XFRM Interfaces for multitenant IPsec

This example configures a multitenant IPsec setup:
- use strongSwan for IPsec setup
- use VLAN subinterfaces for inside VRF access
- XFRM interfaces to connect IPsec tunnels with the VRFs

## ifstate

```yaml
interfaces:

# external interface for IPsec termination
- name: outside
    addresses:
    - 198.51.100.2/31
    link:
        state: up
        kind: physical
        address: 00:50:56:ad:db:ac

# inside base interface
- name: trunk
  link:
    kind: physical
    address: 8c:16:45:dc:b1:ad
    state: up

# first tenant VRF
- name: vrf-tenant1
    addresses: []
    link:
    state: up
    kind: vrf
    vrf_table: 101

- name: ipsec-tenant1
    addresses: []
    link:
        state: up
        kind: xfrm
        xfrm_link: outside
        xfrm_if_id: 1
        master: vrf-tenant1

- name: inside-tenant1
    addresses:
    - 192.0.2.1/24
    link:
        state: up
        kind: vlan
        link: trunk
        vlan_id: 41
        master: vrf-tenant1


# second tenant VRF
- name: vrf-tenant2
    addresses: []
    link:
    state: up
    kind: vrf
    vrf_table: 102

- name: ipsec-tenant2
    addresses: []
    link:
        state: up
        kind: xfrm
        xfrm_link: outside
        xfrm_if_id: 2
        master: vrf-tenant2

- name: inside-tenant2
    addresses:
    - 192.0.2.1/24
    link:
        state: up
        kind: vlan
        link: trunk
        vlan_id: 42
        master: vrf-tenant2


routing:
    routes:
    # outside default route
    - to: 0.0.0.0/0
      via: 198.51.100.1

    # first tenant VRF: add default route into vpn
    - to: 0.0.0.0/0
      dev: ipsec-tenant1
      table: 101

    # second tenant VRF: add default route into vpn
    - to: 0.0.0.0/0
      dev: ipsec-tenant2
      table: 102

```


## strongSwan

```json
connections {
    # Section for an IKE connection named <conn>.
    tentant1 {
        # IKE major version to use for connection.
        version = 2

        # Local address(es) to use for IKE communication, comma separated.
        local_addrs = 198.51.100.2

        # Remote address(es) to use for IKE communication, comma separated.
        remote_addrs = 203.0.113.1

        # Default inbound XFRM interface ID for children.
        if_id_in = 101

        # Default outbound XFRM interface ID for children.
        if_id_out = 101

        # Section for a local authentication round.
        local {
            auth = psk
        }

        # Section for a remote authentication round.
        remote {
            auth = psk
        }

        children {
            # CHILD_SA configuration sub-section.
            tenant1 {
                # Local traffic selectors to include in CHILD_SA.
                local_ts = 192.0.2.0/24

                # Remote selectors to include in CHILD_SA.
                remote_ts = 0.0.0.0/0
            }
        }
    }
}

connections {
    # Section for an IKE connection named <conn>.
    tentant2 {
        # IKE major version to use for connection.
        version = 2

        # Local address(es) to use for IKE communication, comma separated.
        local_addrs = 198.51.100.2

        # Remote address(es) to use for IKE communication, comma separated.
        remote_addrs = 203.0.113.1

        # Default inbound XFRM interface ID for children.
        if_id_in = 102

        # Default outbound XFRM interface ID for children.
        if_id_out = 102

        # Section for a local authentication round.
        local {
            auth = psk
        }

        # Section for a remote authentication round.
        remote {
            auth = psk
        }

        children {
            # CHILD_SA configuration sub-section.
            tenant1 {
                # Local traffic selectors to include in CHILD_SA.
                local_ts = 192.0.2.0/24

                # Remote selectors to include in CHILD_SA.
                remote_ts = 0.0.0.0/0
            }
        }
    }
}
```
