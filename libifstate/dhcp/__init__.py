from libifstate.util import logger, IfStateLogging
import pyroute2.netns

class DHCP():
    def __init__(self, netns, iface, dhcp):
        self.netns = netns
        self.iface = iface
        self.dhcp = dhcp

    def apply(self, do_apply):

        # if self.netns.netns is not None:
        #     pyroute2.netns.pushns(self.netns.netns)

        # try:
        #     self.wg = WG()
        # finally:
        #     if self.netns.netns is not None:
        #         pyroute2.netns.popns()
        pass
