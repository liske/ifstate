from libifstate.util import logger, IfStateLogging, IPRouteExt, NetNSExt, root_ipr
from libifstate.sysctl import Sysctl

import atexit
from copy import deepcopy
import logging
import pyroute2
import re
import secrets
import shutil
import subprocess

netns_name_map = {}
netns_name_root = None
netns_nsid_map = {}
findmnt_cmd = shutil.which('findmnt')

if findmnt_cmd is None:
    logger.debug("findmnt binary is not available, netns binding of links might not be correct")

@atexit.register
def close_netns():
    for netns in netns_name_map.values():
        netns.close()

    if netns_name_root is not None:
        pyroute2.netns.remove(netns_name_root)

class NetNameSpace():
    def __init__(self, name):
        self.netns = name
        self.links = {}
        self.addresses = {}
        self.bpf_progs = None
        self.fdb = {}
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
            self.ipr = root_ipr
            self.mount = b''
        else:
            self.ipr = NetNSExt(name)
            netns_name_map[name] = self.ipr
            if findmnt_cmd is None:
                self.mount = name.encode("utf-8")
            else:
                self.mount = subprocess.check_output([findmnt_cmd, '-f', '-J', "/run/netns/{}".format(name)])

    def __deepcopy__(self, memo):
        '''
        Add custom deepcopy implementation to keep single IPRoute and NetNS instances.
        '''
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'ipr':
                setattr(result, k, v)
            else:
                setattr(result, k, deepcopy(v, memo))
        return result

    def get_netnsid(self, peer_netns_name):
        if peer_netns_name is None:
            peer_ipr = root_ipr
            peer_pid = 1
        else:
            peer_ipr = netns_name_map[peer_netns_name]
            peer_pid = peer_ipr.child

        result = self.ipr.get_netnsid(pid=peer_pid)
        if result['nsid'] == 4294967295:
            self.ipr.set_netnsid(pid=peer_pid)
            result = self.ipr.get_netnsid(pid=peer_pid)

        peer_nsid = result['nsid']

        return (peer_ipr, peer_nsid)

def prepare_netns(do_apply, target_netns_list, new_netns_list):
    logger.info("configure network namespaces...")

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
            logger.log_del(name)

            if do_apply:
                pyroute2.netns.remove(name)

        # create missing netns
        elif name not in current_netns_list or name in new_netns_list:
            logger.log_add(name)

        # log already existing namespaces
        else:
            logger.log_ok(name)

def get_netns_root():
    global netns_name_root

    if netns_name_root is not None:
        return netns_name_root

    while True:
        name = "ifstate.root.{}".format(secrets.token_hex(2))
        if not name in netns_name_map:
            pyroute2.netns.attach(name, 1)
            netns_name_root = name
            return name

def get_netns_instances():
    netns_instances = []
    for netns_name in pyroute2.netns.listnetns():
        try:
            netns_instances.append(NetNameSpace(netns_name))
        except OSError as ex:
            if ex.errno == 22:
                logger.warn("Cannot open netns %s: %s", netns_name, ex.strerror)
            else:
               raise ex

    return netns_instances

class LinkRegistry():
    def __init__(self, ignores, root_netns):
        self.ignores = ignores
        self.root_netns = root_netns

        self.rebuild_registry()

    def __deepcopy__(self, memo):
        '''
        Add custom deepcopy implementation to refresh LinkRegistry on copy.
        '''
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k != 'registry':
                setattr(result, k, deepcopy(v, memo))
        result.rebuild_registry()
        return result

    def rebuild_registry(self):
        self.registry = []

        self.inventory_netns(self.root_netns)
        for namespace in get_netns_instances():
            self.inventory_netns(namespace)

        if logger.getEffectiveLevel() <= logging.DEBUG:
            self.debug_dump()

    def add_link(self, netns, link):
        item = LinkRegistryItem(
            self,
            netns,
            link,
        )
        self.registry.append(item)
        return item

    def get_link(self, **attributes):
        for link in self.registry:
            if link.match(**attributes):
                return link
        return None

    def inventory_netns(self, target_netns):
        for link in target_netns.ipr.get_links():
            self.registry.append(LinkRegistryItem(
                self,
                target_netns,
                link,
            ))

    def get_random_name(self, prefix):
        hex_length = int((15-len(prefix))/2)
        free = False
        while True:
            ifname = prefix + token_hex(hex_length)
            if self.get_link({'ifname': ifname}) is None:
                return ifname

    def debug_dump(self):
        logger.debug('link registry dump:')
        for item in self.registry:
            logger.debug('  %s', item)

class LinkRegistryItem():
    def __init__(self, registry, netns, link):
        self.registry = registry
        self.netns = netns
        self.link = None
        self.attributes = {
            'index': link['index'],
            'ifname': link.get_attr('IFLA_IFNAME'),
            'address': link.get_attr('IFLA_ADDRESS'),
        }
        self.state = link['state']

        linkinfo = link.get_attr('IFLA_LINKINFO')
        if linkinfo and linkinfo.get_attr('IFLA_INFO_KIND') != None:
            self.attributes['kind'] = linkinfo.get_attr('IFLA_INFO_KIND')
        else:
            self.attributes['kind'] = "physical"
            self.attributes['businfo'] = self.netns.ipr.get_businfo(self.attributes['ifname'])
            self.attributes['permaddr'] = link.get_attr('IFLA_PERM_ADDRESS')

        self.attributes['netns'] =self.netns.netns

    def __ipr_link(self, command, **kwargs):
        logger.debug("ip link set netns={} {}".format(
            self.netns.netns,
            " ".join("{}={}".format(k, v) for k, v in kwargs.items())
        ), extra={'netns': self.netns})

        self.netns.ipr.link(command, **kwargs)

    @property
    def index(self):
        return self.attributes['index']

    def match(self, **kwargs):
        for attr, value in kwargs.items():
            if self.attributes.get(attr) != value:
                return False

        return True

    def update_ifname(self, ifname):
        self.attributes['ifname'] = ifname
        self.__ipr_link('set', index=self.attributes['index'], state='down')
        self.__ipr_link('set', index=self.attributes['index'], ifname=ifname)

    def update_netns(self, netns):
        if netns.netns:
            netns_name = netns.netns
        else:
            netns_name = get_netns_root()

        idx = next(iter(netns.ipr.link_lookup(ifname=self.attributes['ifname'])), None)
        if idx is not None:
            # ToDo
            self.update_ifname( self.link_registry.get_random_name('__netns__') )

        self.__ipr_link('set', index=self.attributes['index'], net_ns_fd=netns_name)
        self.netns = netns
        self.attributes['index'] = next(iter(self.netns.ipr.link_lookup(ifname=self.attributes['ifname'])), None)

    def __repr__(self):
        attributes = []
        for attr in sorted(self.attributes.keys()):
            if attr != 'ifname':
                attributes.append(f"{attr}={self.attributes[attr]}")

        if self.link is not None:
            tag = '*'
        elif any(re.match(regex, self.attributes['ifname']) for regex in self.registry.ignores):
            tag = '='
        else:
            tag = ''

        return  f"{self.attributes['ifname']}{tag}[{', '.join(attributes)}]"
