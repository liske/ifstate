from libifstate.util import logger, IfStateLogging, IPRouteExt, NetNSExt
from libifstate.sysctl import Sysctl

import atexit

netns_list = []

@atexit.register
def close_netns():
    for netns in netns_list:
        netns.close()

class NetNS():
    def __init__(self, name):
        self.netns = name
        self.links = {}
        self.addresses = {}
        self.neighbours = {}
        self.vrrp = {
            'links': [],
            'group': {},
            'instance': {},
        }
        self.tables = None
        self.rules = None
        self.sysctl = Sysctl(self)
        self.tc = {}
        self.wireguard = {}
        self.xdp = {}

        if name is None:
            self.ipr = IPRouteExt()
        else:
            self.ipr = NetNSExt(name)
            netns_list.append(self.ipr)
