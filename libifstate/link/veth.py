from libifstate.util import logger, ipr
from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

class VethLink(Link):
    def __init__(self, name, link, ethtool, vrrp):
        super().__init__(name, link, ethtool, vrrp)

    # quirk to handle peer attribute
    def get_if_attr(self, key):
        if key != "peer":
            return super().get_if_attr(key)

        peer = super().get_if_attr("link")

        if peer is None:
            return None

        lnk = next(iter(ipr.get_links(peer)), None)
        return lnk.get_attr("IFLA_IFNAME")
