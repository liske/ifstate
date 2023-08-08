from libifstate.util import logger, IfStateLogging, IPRouteExt, NetNSExt
from libifstate.sysctl import Sysctl
import pyroute2

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

def prepare_netns(do_apply, target_netns_list):
    logger.info("configuring network namespaces")

    # get mapping of netns names to lists of pids
    ns_pids = pyroute2.netns.ns_pids()

    # build unique list of current and target netns names
    current_netns_list = pyroute2.netns.listnetns()
    names_set = set(list(target_netns_list) + current_netns_list)

    for name in sorted(names_set):
        # cleanup orphan netns
        if name not in target_netns_list:
            if name in ns_pids:
                logger.warning(
                    'pids: {}'.format(', '.join((str(x) for x in ns_pids[name]))),
                    extra={'iface': name})
            logger.info('del', extra={'iface': name, 'style': IfStateLogging.STYLE_DEL})

            if do_apply:
                pyroute2.netns.remove(name)

        # create missing netns
        elif name not in current_netns_list:
            logger.info('add', extra={'iface': name, 'style': IfStateLogging.STYLE_CHG})

        # log already existing namespaces
        else:
            logger.info('ok', extra={'iface': name, 'style': IfStateLogging.STYLE_OK})
