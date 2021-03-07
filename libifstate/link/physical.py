from libifstate.util import logger
from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

class PhysicalLink(Link):
    def __init__(self, name, link, ethtool, vrrp):
        super().__init__(name, link, ethtool, vrrp)
        self.cap_create = False
        self.cap_ethtool = True
        self.ethtool = ethtool
 
    def create(self, do_apply, oper="add"):
        logger.warning('Unable to create missing physical link: {}'.format(self.settings.get('ifname')))
