from libifstate.util import logger
from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

from pwd import getpwnam
from grp import getgrnam

class TunLink(Link):
    def __init__(self, ifstate, netns, name, link, ethtool, vrrp, brport):
        if 'tun_owner' in link and isinstance(link['tun_owner'], str):
            link['tun_owner'] = getpwnam(link['tun_owner'])[2]

        if 'tun_group' in link and isinstance(link['tun_group'], str):
            link['tun_group'] = getgrnam(link['tun_group'])[2]

        super().__init__(ifstate, netns, name, link, ethtool, vrrp, brport)
        self.cap_create = bool(link.get('tun_persist'))
 
    def create(self, do_apply, sysctl, excpts, oper="add"):
        if not self.cap_create:
            logger.warning('Unable to create missing non-persistent tuntap link: {}'.format(self.settings.get('ifname')))
        else:
            super().create(do_apply, sysctl, excpts, oper)
