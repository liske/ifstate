from libifstate.exception import LinkDuplicate
from libifstate.link.base import ethtool_path, Link
from libifstate.address import Addresses
from libifstate.neighbour import Neighbours
from libifstate.routing import Tables, Rules, RTLookups
from libifstate.sysctl import Sysctl
from libifstate.parser import Parser
from libifstate.tc import TC
from libifstate.exception import netlinkerror_classes

from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_PERMANENT
try:
    from libifstate.wireguard import WireGuard
except ModuleNotFoundError:
    # ignore missing plugin
    pass
except Exception as err:
    # ignore plugin failure if kmod is not loaded
    if not isinstance(err, netlinkerror_classes):
        raise

try:
    from libifstate.bpf import libbpf, BPF

    try:
        from libifstate.xdp import XDP
    except ModuleNotFoundError:
        # ignore missing plugin
        pass
except ModuleNotFoundError:
    # ignore missing plugin
    pass

from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import FeatureMissingError, LinkCircularLinked, LinkNoConfigFound, ParserValidationError
from ipaddress import ip_network, ip_interface
from jsonschema import validate, ValidationError, FormatChecker
from copy import deepcopy
import os
import pkgutil
import re
import json
import errno
import logging

__version__ = "1.8.2"


class IfState():
    def __init__(self):
        logger.debug('IfState {}'.format(__version__))
        self.links = {}
        self.addresses = {}
        self.bpf_progs = None
        self.neighbours = {}
        self.ignore = {}
        self.vrrp = {
            'links': [],
            'group': {},
            'instance': {},
        }
        self.tables = None
        self.rules = None
        self.sysctl = Sysctl()
        self.tc = {}
        self.wireguard = {}
        self.xdp = {}
        self.features = {
            'brport': True,
            'link': True,
            'sysctl': os.access('/proc/sys/net', os.R_OK),
            'ethtool': not ethtool_path is None,
            'tc': True,
            'wireguard': not globals().get("WireGuard") is None,
            'bpf': not globals().get("libbpf") is None,
            'xdp': not globals().get("XDP") is None,
        }

        logger.debug('{}'.format(' '.join(sorted(
            [x for x, y in self.features.items() if y]))), extra={'iface': 'features'})

        if self.features['bpf']:
            if logger.level != logging.DEBUG:
                # BPF: disable libbpf stderr output
                libbpf.libbpf_set_print(0)

    def update(self, ifstates, soft_schema):
        # check config schema
        schema = json.loads(pkgutil.get_data(
            "libifstate", "../schema/ifstate.conf.schema.json"))
        try:
            validate(ifstates, schema, format_checker=FormatChecker())
        except ValidationError as ex:
            if len(ex.path) > 0:
                path = ["$"]
                for i, p in enumerate(ex.absolute_path):
                    if type(p) == int:
                        path.append("[{}]".format(p))
                    else:
                        path.append(".")
                        path.append(p)

                detail = "{}: {}".format("".join(path), ex.message)
            else:
                detail = ex.message
            if soft_schema:
                logger.error("Config validation failed for {}".format(detail))
            else:
                raise ParserValidationError(detail)

        # parse options
        if 'options' in ifstates:
            # parse global sysctl settings
            if 'sysctl' in ifstates['options']:
                for iface in ['all', 'default']:
                    if iface in ifstates['options']['sysctl']:
                        self.sysctl.add(
                            iface, ifstates['options']['sysctl'][iface])

        # load BPF programs
        if 'bpf' in ifstates:
            if not self.features['bpf']:
                raise FeatureMissingError("bpf")

            if self.bpf_progs is None:
                self.bpf_progs = BPF()
            for name, config in ifstates['bpf'].items():
                self.bpf_progs.add(name, config)

        # add interfaces from config
        for ifstate in ifstates['interfaces']:
            name = ifstate['name']
            if name in self.links:
                raise LinkDuplicate()
            if 'link' in ifstate:
                self.links[name] = Link(
                    name, ifstate['link'], ifstate.get('ethtool'), ifstate.get('vrrp'), ifstate.get('brport'))
            else:
                self.links[name] = None

            if 'addresses' in ifstate:
                self.addresses[name] = Addresses(name, ifstate['addresses'])
            else:
                self.addresses[name] = None

            if 'neighbours' in ifstate:
                self.neighbours[name] = Neighbours(name, ifstate['neighbours'])
            else:
                self.neighbours[name] = None

            if 'vrrp' in ifstate:
                ktype = ifstate['vrrp']['type']
                kname = ifstate['vrrp']['name']
                kstates = ifstate['vrrp']['states']
                if not kname in self.vrrp[ktype]:
                    self.vrrp[ktype][kname] = {}
                for kstate in kstates:
                    if not kstate in self.vrrp[ktype][kname]:
                        self.vrrp[ktype][kname][kstate] = []
                    self.vrrp[ktype][kname][kstate].append(name)
                self.vrrp['links'].append(name)

            if 'sysctl' in ifstate:
                self.sysctl.add(name, ifstate['sysctl'])

            if 'cshaper' in ifstate:
                profile_name = ifstate['cshaper'].get(
                    'profile', 'default')
                logger.debug('cshaper profile {} enabled'.format(profile_name),
                             extra={'iface': name})
                cshaper_profile = ifstates['cshaper'][profile_name]

                # ingress
                ifb_name = re.sub(
                    cshaper_profile['ingress_ifname']['search'], cshaper_profile['ingress_ifname']['replace'], name)
                logger.debug('cshaper ifb name {}'.format(ifb_name),
                             extra={'iface': name})

                ifb_state = {
                    'name': ifb_name,
                    'link': {
                        'state': 'up',
                        'kind': 'ifb',
                    },
                    'tc': {
                        'qdisc': cshaper_profile['ingress_qdisc'],
                    }
                }
                ifb_state['tc']['qdisc']['bandwidth'] = ifstate['cshaper'].get(
                    'ingress', 'unlimited')

                ifstates['interfaces'].append(ifb_state)

                # egress
                if 'tc' in ifstate:
                    logger.warning(
                        'cshaper settings replaces tc settings', extra={'iface': name})

                ifstate['tc'] = {
                    'ingress': True,
                    'qdisc': cshaper_profile['egress_qdisc'],
                    'filter': [
                        {
                            'kind': 'matchall',
                            'parent': 'ffff:',
                            'action': [
                                {
                                    'kind': 'mirred',
                                    'direction': 'egress',
                                    'action': 'redirect',
                                    'dev': ifb_name,
                                }
                            ]
                        }

                    ]
                }

                ifstate['tc']['qdisc']['bandwidth'] = ifstate['cshaper'].get(
                    'egress', 'unlimited')

                del ifstate['cshaper']

            if 'tc' in ifstate:
                self.tc[name] = TC(
                    name, ifstate['tc'])

            if 'wireguard' in ifstate:
                if not self.features['wireguard']:
                    raise FeatureMissingError("wireguard")

                self.wireguard[name] = WireGuard(name, ifstate['wireguard'])

            if 'xdp' in ifstate:
                if not self.features['xdp']:
                    raise FeatureMissingError("xdp")

                self.xdp[name] = XDP(name, ifstate['xdp'])

        # add routing from config
        if 'routing' in ifstates:
            if 'routes' in ifstates['routing']:
                if self.tables is None:
                    self.tables = Tables()
                for route in ifstates['routing']['routes']:
                    self.tables.add(route)

            if 'rules' in ifstates['routing']:
                if self.rules is None:
                    self.rules = Rules()
                for rule in ifstates['routing']['rules']:
                    self.rules.add(rule)

        # add ignore list items
        self.ignore.update(ifstates['ignore'])

    def apply(self, vrrp_type=None, vrrp_name=None, vrrp_state=None):
        self._apply(True, vrrp_type, vrrp_name, vrrp_state)

    def check(self, vrrp_type=None, vrrp_name=None, vrrp_state=None):
        self._apply(False, vrrp_type, vrrp_name, vrrp_state)

    def _apply(self, do_apply, vrrp_type, vrrp_name, vrrp_state):
        vrrp_ignore = []
        vrrp_remove = []

        by_vrrp = not None in [
            vrrp_type, vrrp_name, vrrp_state]

        for ifname, link in self.links.items():
            if ifname in self.vrrp['links']:
                if not by_vrrp:
                    vrrp_ignore.append(ifname)
                else:
                    if not link.match_vrrp_select(vrrp_type, vrrp_name):
                        vrrp_ignore.append(ifname)
                    elif not vrrp_name in self.vrrp[vrrp_type] or not vrrp_state in self.vrrp[vrrp_type][vrrp_name] or not ifname in self.vrrp[vrrp_type][vrrp_name][vrrp_state]:
                        vrrp_remove.append(ifname)
            elif by_vrrp:
                vrrp_ignore.append(ifname)

        self.ipaddr_ignore = set()
        for ip in self.ignore.get('ipaddr', []):
            self.ipaddr_ignore.add(ip_network(ip))

        if not any(not x is None for x in self.links.values()):
            logger.error("DANGER: Not a single link config has been found!")
            raise LinkNoConfigFound()

        for iface in ['all', 'default']:
            if self.sysctl.has_settings(iface):
                logger.info("\nconfiguring {} interface sysctl".format(iface))
                self.sysctl.apply(iface, do_apply)

        if not self.bpf_progs is None:
            self.bpf_progs.apply(do_apply)

        for stage in range(2):
            if stage == 0:
                logger.info("\nconfiguring interface links")

                for ifname in vrrp_remove:
                    logger.debug('to be removed due to vrrp constraint',
                                 extra={'iface': ifname})
                    del self.links[ifname]
            else:
                logger.info("\nconfiguring interface links (stage 2)")

            retry = False
            applied = []
            while len(applied) + len(vrrp_ignore) < len(self.links):
                last = len(applied)
                for name, link in self.links.items():
                    if name in applied:
                        continue

                    if name in vrrp_ignore:
                        logger.debug('skipped due to vrrp constraint',
                                     extra={'iface': name})
                        continue

                    if link is None:
                        logger.debug('skipped due to no link settings',
                                     extra={'iface': name})
                        applied.append(name)
                    else:
                        deps = link.depends()
                        if all(x in applied for x in deps):
                            excpts = link.apply(do_apply, self.sysctl)
                            if excpts.has_errno(errno.EEXIST):
                                retry = True
                            applied.append(name)
                if last == len(applied):
                    raise LinkCircularLinked()

            for link in ipr.get_links():
                name = link.get_attr('IFLA_IFNAME')
                # skip links on ignore list
                if not name in self.links and not any(re.match(regex, name) for regex in self.ignore.get('ifname', [])):
                    info = link.get_attr('IFLA_LINKINFO')
                    # remove virtual interface
                    if info is not None:
                        kind = info.get_attr('IFLA_INFO_KIND')
                        logger.info(
                            'del', extra={'iface': name, 'style': IfStateLogging.STYLE_DEL})
                        if do_apply:
                            try:
                                ipr.link('set', index=link.get(
                                    'index'), state='down')
                                ipr.link('del', index=link.get('index'))
                            except Exception as err:
                                if not isinstance(err, netlinkerror_classes):
                                    raise
                                logger.warning('removing link {} failed: {}'.format(
                                    name, err.args[1]))
                    # shutdown physical interfaces
                    else:
                        if name in vrrp_ignore:
                            logger.warning('vrrp', extra={
                                'iface': name, 'style': IfStateLogging.STYLE_OK})
                        if link.get('state') == 'down':
                            logger.warning('orphan', extra={
                                'iface': name, 'style': IfStateLogging.STYLE_OK})
                        else:
                            logger.warning('orphan', extra={
                                'iface': name, 'style': IfStateLogging.STYLE_CHG})
                            if do_apply:
                                try:
                                    ipr.link('set', index=link.get(
                                        'index'), state='down')
                                except Exception as err:
                                    if not isinstance(err, netlinkerror_classes):
                                        raise
                                    logger.warning('updating link {} failed: {}'.format(
                                        name, err.args[1]))
            if not retry:
                break

        if any(not x is None for x in self.tc.values()):
            logger.info("\nconfiguring interface traffic control...")

            for name, tc in self.tc.items():
                if name in vrrp_ignore:
                    logger.debug('skipped due to vrrp constraint',
                                 extra={'iface': name})
                elif tc is None:
                    logger.debug('skipped due to no tc settings', extra={
                                 'iface': name})
                else:
                    tc.apply(do_apply)

        if any(not x is None for x in self.xdp.values()):
            logger.info("\nconfiguring eXpress Data Path...")

            for name, xdp in self.xdp.items():
                if name in vrrp_ignore:
                    logger.debug('skipped due to vrrp constraint',
                                 extra={'iface': name})
                elif xdp is None:
                    logger.debug('skipped due to no xdp settings', extra={
                                 'iface': name})
                else:
                    xdp.apply(do_apply, self.bpf_progs)

        if any(not x is None for x in self.addresses.values()):
            logger.info("\nconfiguring interface ip addresses...")
            # add empty objects for unhandled interfaces
            for link in ipr.get_links():
                name = link.get_attr('IFLA_IFNAME')
                # skip links on ignore list
                if not name in self.addresses and not any(re.match(regex, name) for regex in self.ignore.get('ifname', [])):
                    self.addresses[name] = Addresses(name, [])

            for name, addresses in self.addresses.items():
                if name in vrrp_ignore:
                    logger.debug('skipped due to vrrp constraint',
                                 extra={'iface': name})
                elif addresses is None:
                    logger.debug('skipped due to no address settings', extra={
                                 'iface': name})
                else:
                    addresses.apply(self.ipaddr_ignore, self.ignore.get(
                        'ipaddr_dynamic', True), do_apply)
        else:
            logger.debug("\nno interface ip addressing to be applied")

        if any(not x is None for x in self.neighbours.values()):
            logger.info("\nconfiguring interface neighbours...")
            # add empty objects for unhandled interfaces
            for link in ipr.get_links():
                name = link.get_attr('IFLA_IFNAME')
                # skip links on ignore list
                if not name in self.neighbours and not any(re.match(regex, name) for regex in self.ignore.get('ifname', [])):
                    self.neighbours[name] = Neighbours(name, [])

            for name, neighbours in self.neighbours.items():
                if name in vrrp_ignore:
                    logger.debug('skipped due to vrrp constraint',
                                 extra={'iface': name})
                elif neighbours is None:
                    logger.debug('skipped due to no address settings', extra={
                                 'iface': name})
                else:
                    neighbours.apply(do_apply)
        else:
            logger.debug("\nno interface neighbours to be applied")

        if not self.tables is None:
            self.tables.apply(self.ignore.get('routes', []), do_apply)

        if not self.rules is None:
            self.rules.apply(self.ignore.get('rules', []), do_apply)

        if len(self.wireguard):
            logger.info("\nconfiguring WireGuard...")
            for iface, wireguard in self.wireguard.items():
                if iface in vrrp_ignore:
                    logger.debug('skipped due to vrrp constraint',
                                 extra={'iface': name})
                    continue
                wireguard.apply(do_apply)

    def show(self, showall=False):
        if showall:
            defaults = deepcopy(Parser._default_ifstates)
        else:
            defaults = {}

        ipaddr_ignore = []
        for ip in Parser._default_ifstates['ignore']['ipaddr_builtin']:
            ipaddr_ignore.append(ip_network(ip))

        ifs_links = []
        for ipr_link in ipr.get_links():
            name = ipr_link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not any(re.match(regex, name) for regex in Parser._default_ifstates['ignore']['ifname_builtin']):
                ifs_link = {
                    'name': name,
                    'addresses': [],
                    'link': {
                        'state': ipr_link['state'],
                    },
                }

                for addr in ipr.get_addr(index=ipr_link['index']):
                    if addr['flags'] & IFA_F_PERMANENT == IFA_F_PERMANENT:
                        ip = ip_interface(addr.get_attr(
                            'IFA_ADDRESS') + '/' + str(addr['prefixlen']))
                        if not any(ip in net for net in ipaddr_ignore):
                            ifs_link['addresses'].append(ip.with_prefixlen)

                info = ipr_link.get_attr('IFLA_LINKINFO')
                if info is None:
                    kind = None
                else:
                    kind = info.get_attr('IFLA_INFO_KIND')
                if kind is not None:
                    ifs_link['link']['kind'] = kind

                    data = info.get_attr('IFLA_INFO_DATA')
                    # unsupported link type, fallback to raw encoding
                    if data is not None and type(data) != str:
                        for k, v in data['attrs']:
                            if k not in ['UNKNOWN', 'IFLA_VLAN_FLAGS']:
                                attr = ipr_link.nla2name(k)
                                if attr in Link.attr_value_maps:
                                    ifs_link['link'][attr] = Link.attr_value_maps[attr].get(
                                        v, v)
                                elif attr in Link.attr_value_lookup:
                                    ifs_link['link'][attr] = Link.attr_value_lookup[attr].lookup_str(v)
                                else:
                                    ifs_link['link'][attr] = v
                else:
                    ifs_link['link']['kind'] = 'physical'
                    addr = ipr_link.get_attr('IFLA_ADDRESS')
                    if not addr is None:
                        ifs_link['link']['address'] = addr
                    permaddr = ipr.get_permaddr(name)
                    if not permaddr is None:
                        if addr is None:
                            ifs_link['link']['addr'] = permaddr
                        elif addr != permaddr:
                            ifs_link['link']['permaddr'] = permaddr
                    businfo = ipr.get_businfo(name)
                    if not businfo is None:
                        ifs_link['link']['businfo'] = businfo

                # add device group if not 0
                group = ipr_link.get_attr('IFLA_GROUP')
                if not group is None and group != 0:
                    ifs_link['link']['group'] = RTLookups.group.lookup_str(group)

                for attr in ['link', 'master', 'gre_link', 'ip6gre_link', 'vxlan_link', 'xfrm_link']:
                    ref = ipr_link.get_attr('IFLA_{}'.format(attr.upper()))
                    if ref is not None:
                        try:
                            ifs_link['link'][attr] = ipr.get_ifname_by_index(
                                ref)
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            logger.warning('lookup {} failed: {}'.format(
                                attr, err.args[1]), extra={'iface': name})
                            ifs_link['link'][attr] = ref

                mtu = ipr_link.get_attr('IFLA_MTU')
                if not mtu is None and not mtu in [1500, 65536]:
                    ifs_link['link']['mtu'] = mtu

                brport.BRPort.show(showall, ipr_link['index'], ifs_link)

                ifs_links.append(ifs_link)

        routing = {
            'routes': Tables().show_routes(Parser._default_ifstates['ignore']['routes_builtin']),
            'rules': Rules().show_rules(Parser._default_ifstates['ignore']['rules_builtin']),
        }

        return {**defaults, **{'interfaces': ifs_links, 'routing': routing}}
