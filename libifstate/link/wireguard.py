from libifstate.link.base import Link
from wgnlpy import WireGuard as WG

class WireguardLink(Link):
    def __init__(self, name, link, ethtool):
        super().__init__(name, link, ethtool)
 
    def create(self):
        pass
