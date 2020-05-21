from libifstate.link.base import Link

class VlanLink(Link):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.attr_map.update({
            'vlan_id': ['IFLA_LINKINFO', 'IFLA_INFO_DATA', 'IFLA_VLAN_ID'],
            'vlan_protocol': ['IFLA_LINKINFO', 'IFLA_INFO_DATA', 'IFLA_VLAN_PROTOCOL'],
        })
        self.attr_idx.append('link')

    def depends(self):
        return self.settings['link']
