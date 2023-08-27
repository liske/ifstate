from libifstate.util import logger
from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

class VethLink(Link):
    def __init__(self, ifstate, netns, name, link, ethtool, vrrp, brport):
        super().__init__(ifstate, netns, name, link, ethtool, vrrp, brport)

    # quirk to handle peer attribute
    def get_if_attr(self, key):
        if key != "peer":
            return super().get_if_attr(key)

        peer = super().get_if_attr("link")

        if peer is None:
            return None

        lnk = next(iter(self.netns.ipr.get_links(peer)), None)
        return lnk.get_attr("IFLA_IFNAME")
