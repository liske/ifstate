from libifstate.exception import LinkDuplicate
from libifstate.link.base import ethtool_path, Link
from libifstate.address import Addresses
from libifstate.fdb import FDB
from libifstate.neighbour import Neighbours
from libifstate.routing import Tables, Rules, RTLookups
from libifstate.parser import Parser
from libifstate.tc import TC
from libifstate.exception import netlinkerror_classes
import bisect
import pyroute2

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

from libifstate.netns import NetNameSpace, prepare_netns, LinkRegistry
from libifstate.util import logger, IfStateLogging, LinkDependency
from libifstate.exception import FeatureMissingError, LinkCircularLinked, LinkNoConfigFound, ParserValidationError
from ipaddress import ip_network, ip_interface
from jsonschema import validate, ValidationError, FormatChecker
from copy import deepcopy
import os
import pkgutil
import re
import secrets
import json
import errno
import logging

__version__ = "1.11.2"


class IfState():
    def __init__(self):
        logger.debug('IfState {}'.format(__version__))

        self.namespaces = None
        self.root_netns = NetNameSpace(None)
        self.defaults = []
        self.ignore = {}
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

        # add interface defaults
        if 'defaults' in ifstates:
            self.defaults = ifstates['defaults']

        # add ignore list items
        self.ignore.update(ifstates['ignore'])
        self.ipaddr_ignore = set()
        for ip in self.ignore.get('ipaddr', []):
            self.ipaddr_ignore.add(ip_network(ip))

        # save cshaper profiles
        self.cshaper_profiles = ifstates['cshaper']

        # build link registry over all named netns
        self.link_registry = LinkRegistry(self.ignore.get('ifname', []), self.root_netns)

        self._update(self.root_netns, ifstates)
        if 'namespaces' in ifstates:
            self.namespaces = {}
            self.new_namespaces = []
            for netns_name, netns_ifstates in ifstates['namespaces'].items():
                is_new = netns_name not in pyroute2.netns.listnetns()
                self.namespaces[netns_name] = NetNameSpace(netns_name)
                if is_new:
                    self.new_namespaces.append(netns_name)
                    self.link_registry.inventory_netns(self.namespaces[netns_name])
                self._update(self.namespaces[netns_name], netns_ifstates)

    def _update(self, netns, ifstates):
        # parse options
        if 'options' in ifstates:
            # parse global sysctl settings
            if 'sysctl' in ifstates['options']:
                for proto in  ifstates['options']['sysctl'].keys():
                    if proto in ['all', 'default']:
                        netns.sysctl.add(
                            proto, ifstates['options']['sysctl'][proto])
                    else:
                        netns.sysctl.add_global(
                            proto, ifstates['options']['sysctl'][proto])

        # load BPF programs
        if 'bpf' in ifstates:
            if not self.features['bpf']:
                raise FeatureMissingError("bpf")

            if netns.bpf_progs is None:
                netns.bpf_progs = BPF(netns)
            for name, config in ifstates['bpf'].items():
                netns.bpf_progs.add(name, config)

        # add interfaces from config
        for ifstate in ifstates['interfaces']:
            name = ifstate['name']
            kind = ifstate['link']['kind']
            defaults = self.get_defaults(
                ifname=name,
                kind=kind)

            if name in netns.links:
                raise LinkDuplicate()

            # prepare ethtool settings
            if name != 'lo':
                ethtool = {}
                if 'ethtool' in defaults:
                    ethtool.update(defaults['ethtool'])
                for k, v in ifstate.get('ethtool', {}).items():
                    if k in ethtool:
                        ethtool[k].update(v)
                    else:
                        ethtool[k] = v
                if not ethtool:
                    ethtool = None
            else:
                ethtool = None

            link = {}
            if 'link' in defaults:
                link.update(defaults['link'])
            if 'link' in ifstate:
                link.update(ifstate['link'])
            if link:
                netns.links[name] = Link(self,
                    netns, name, link, ethtool, ifstate.get('vrrp'), ifstate.get('brport'))
            else:
                netns.links[name] = None

            if 'addresses' in ifstate:
                netns.addresses[name] = Addresses(netns, name, ifstate['addresses'])
            elif defaults.get('clear_addresses', False):
                netns.addresses[name] = Addresses(netns, name, [])

            if 'fdb' in ifstate:
                netns.fdb[name] = FDB(netns, name, ifstate['fdb'])
            elif defaults.get('clear_fdb', False):
                netns.fdb[name] = FDB(netns, name, [])

            if 'neighbours' in ifstate:
                netns.neighbours[name] = Neighbours(netns, name, ifstate['neighbours'])
            elif defaults.get('clear_neighbours', False):
                netns.neighbours[name] = Neighbours(netns, name, [])

            if 'vrrp' in ifstate:
                ktype = ifstate['vrrp']['type']
                kname = ifstate['vrrp']['name']
                kstates = ifstate['vrrp']['states']
                if not kname in netns.vrrp[ktype]:
                    netns.vrrp[ktype][kname] = {}
                for kstate in kstates:
                    if not kstate in netns.vrrp[ktype][kname]:
                        netns.vrrp[ktype][kname][kstate] = []
                    netns.vrrp[ktype][kname][kstate].append(name)
                netns.vrrp['links'].append(name)

            if 'sysctl' in ifstate:
                netns.sysctl.add(name, ifstate['sysctl'])

            if 'cshaper' in ifstate:
                profile_name = ifstate['cshaper'].get(
                    'profile', 'default')
                logger.debug('cshaper profile {} enabled'.format(profile_name),
                             extra={'iface': name, 'netns': netns})
                cshaper_profile = deepcopy(self.cshaper_profiles[profile_name])

                # ingress
                ifb_name = re.sub(
                    cshaper_profile['ingress_ifname']['search'], cshaper_profile['ingress_ifname']['replace'], name)
                logger.debug('cshaper ifb name {}'.format(ifb_name),
                             extra={'iface': name, 'netns': netns})

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
                        'cshaper settings replaces tc settings', extra={'iface': name, 'netns': netns})

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
                netns.tc[name] = TC(
                    netns, name, ifstate['tc'])

            if 'wireguard' in ifstate:
                if not self.features['wireguard']:
                    raise FeatureMissingError("wireguard")

                netns.wireguard[name] = WireGuard(netns, name, ifstate['wireguard'])

            if 'xdp' in ifstate:
                if not self.features['xdp']:
                    raise FeatureMissingError("xdp")

                netns.xdp[name] = XDP(netns, name, ifstate['xdp'])

        # add routing from config
        if 'routing' in ifstates:
            if 'routes' in ifstates['routing']:
                if netns.tables is None:
                    netns.tables = Tables(netns)
                for route in ifstates['routing']['routes']:
                    netns.tables.add(route)

            if 'rules' in ifstates['routing']:
                if netns.rules is None:
                    netns.rules = Rules(netns)
                for rule in ifstates['routing']['rules']:
                    netns.rules.add(rule)

    def apply(self, vrrp_type=None, vrrp_name=None, vrrp_state=None):
        self._apply(True, vrrp_type, vrrp_name, vrrp_state)

    def check(self, vrrp_type=None, vrrp_name=None, vrrp_state=None):
        self._apply(False, vrrp_type, vrrp_name, vrrp_state)

    def free_registry_item(self, do_apply, item):
        ifname = item.attributes['ifname']

        log_str = ifname
        if item.netns.netns is not None:
            log_str += "[netns={}]".format(item.netns.netns)

        if item.attributes['kind'] != 'physical':
            # remove virtual interface
            logger.log_del(log_str)
            if do_apply:
                try:
                    item.netns.ipr.link('set', index=item.attributes['index'], state='down')
                    item.netns.ipr.link('del', index=item.attributes['index'])
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('removing link {} failed: {}'.format(
                        ifname, err.args[1]), extra={'netns': item.netns})
            return True
        else:
            # shutdown physical interfaces
            if item.state == 'down':
                logger.log_ok(log_str, 'orphan')
            else:
                logger.log_del(log_str, 'orphan')
                if do_apply:
                    try:
                        item.netns.ipr.link('set', index=item.attributes['index'], state='down')
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('updating link {} failed: {}'.format(
                            ifname, err.args[1]), extra={'netns': item.netns})
            return False

    def _dependencies(self, netns):
        deps = {}
        for ifname, link in netns.links.items():
            deps[LinkDependency(ifname, netns.netns)] = link.depends()

        for ifname, tc in netns.tc.items():
            for fltr in tc.tc.get('filter', []):
                for action in fltr.get('action', []):
                    if 'dev' in action:
                        link = LinkDependency(ifname, netns.netns)
                        dep = LinkDependency(action['dev'], netns.netns)
                        if link in deps:
                            deps[link].append(dep)
                        else:
                            deps[link] = [dep]

        return deps

    def _stages(self, continue_on_circualar):
        def dep(arg):
            '''
                Dependency resolver

            "arg" is a dependency dictionary in which
            the values are the dependencies of their respective keys.
            '''
            d=dict((k, set(arg[k])) for k in arg)
            r=[]
            while d:
                # values not in keys (items without dep)
                t=set(i for v in d.values() for i in v)-set(d.keys())
                # and keys without value (items without dep)
                t.update(k for k, v in d.items() if not v)

                if len(t) == 0:
                    logger.error("Circualar link dependency detected: ")
                    for k, v in d.items():
                        logger.error('  {} => {}'.format(k, ", ".join(map(str, v))))
                    logger.error("")

                    if continue_on_circualar:
                        # remaining link deps cannot be resolved, drop them
                        # if we shall continue
                        return r
                    else:
                        raise LinkCircularLinked()

                # can be done right away
                r.append( sorted(t) )
                # and cleaned up
                d=dict(((k, v-t) for k, v in d.items() if v))
            return r

        dependencies = self._dependencies(self.root_netns)
        if self.namespaces is not None:
            for netns in self.namespaces.values():
                dependencies.update(self._dependencies(netns))

        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.debug('dependencies dump:')
            for ifname, deps in dependencies.items():
                logger.debug('  %s => %s', ifname, ", ".join(map(str, deps)))

        stages = dep(dependencies)

        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.debug('stages dump:')
            i = 1
            for stage in stages:
                logger.debug('  #%d => %s', i, ", ".join(map(str, stage)))
                i += 1

        return stages

    def _apply(self, do_apply, vrrp_type=None, vrrp_name=None, vrrp_state=None):
        # check if called from vrrp hook and ignore non-vrrp interfaces
        by_vrrp = not None in [
            vrrp_type, vrrp_name, vrrp_state]
        if by_vrrp:
            logger.info("triggered by vrrp state change")
            logger.log_change("{} {}".format(vrrp_type, vrrp_name), vrrp_state)
            logger.info("")

            # ifstate schema requires lower case keywords
            vrrp_type = vrrp_type.lower()
            vrrp_state = vrrp_state.lower()

        # create and destroy namespaces to match config
        if not by_vrrp and self.namespaces is not None:
            prepare_netns(do_apply, self.namespaces.keys(), self.new_namespaces)
            logger.info("")

        # get link dependency tree
        stages = self._stages(do_apply)

        # remove any orphan (non-ignored) links
        if not by_vrrp:
            had_cleanup = False
            cleanup_items = []
            for item in self.link_registry.registry:
                ifname = item.attributes['ifname']
                # items without a link are orphan - keep them if they match the ignore regex list...
                if item.link is None and not any(re.match(regex, ifname) for regex in self.ignore.get('ifname', [])):
                    # ...or are in a netns namespace while the config has no `namespaces` setting
                    if self.namespaces is not None or item.netns.netns is None:
                        if not had_cleanup:
                            logger.info("cleanup orphan interfaces...")
                            had_cleanup = True
                        if self.free_registry_item(do_apply, item):
                            cleanup_items.append(item)
                        else:
                            item.attributes['orphan'] = True

            if cleanup_items:
                for item in cleanup_items:
                    self.link_registry.registry.remove(item)

            if had_cleanup:
                logger.info("")

        # dump link registry in verbose mode
        if logger.getEffectiveLevel() <= logging.DEBUG:
            self.link_registry.debug_dump()

        if not by_vrrp:
            # apply bpf settings
            had_bpf = self._apply_bpf(do_apply, self.root_netns)
            if self.namespaces is not None:
                for name, netns in self.namespaces.items():
                    had_bpf = self._apply_bpf(do_apply, netns, had_bpf)
            if had_bpf:
                logger.info("")

            # apply sysctl settings
            had_sysctl = self._apply_sysctl(do_apply, self.root_netns)
            if self.namespaces is not None:
                for name, netns in self.namespaces.items():
                    had_sysctl = self._apply_sysctl(do_apply, netns, had_sysctl)
            if had_sysctl:
                logger.info("")

        # create/modify links in order of dependencies
        logger.info("configure interfaces...")
        for stage in stages:
            for link_dep in stage:
                logger.info(" {}".format(link_dep))
                if link_dep.netns is None:
                    self._apply_iface(do_apply, self.root_netns, link_dep.ifname, by_vrrp, vrrp_type, vrrp_name, vrrp_state)
                else:
                    self._apply_iface(do_apply, self.namespaces[link_dep.netns], link_dep.ifname, by_vrrp, vrrp_type, vrrp_name, vrrp_state)

        # configure routing
        logger.info("")
        logger.info("configure routing...")
        self._apply_routing(do_apply, self.root_netns, by_vrrp, vrrp_type, vrrp_name, vrrp_state)
        if self.namespaces is not None:
            for name, netns in self.namespaces.items():
                self._apply_routing(do_apply, netns, by_vrrp, vrrp_type, vrrp_name, vrrp_state)

    def _apply_bpf(self, do_apply, netns, had_bpf=False):
        if not netns.bpf_progs is None:
            if not had_bpf:
                logger.info("load BPF programs...")
                had_bpf = True
            netns.bpf_progs.apply(do_apply)

        return had_bpf

    def _apply_sysctl(self, do_apply, netns, had_sysctl=False):
        for iface in ['all', 'default']:
            if netns.sysctl.has_settings(iface):
                if not had_sysctl:
                    logger.info("configure sysctl settings...")
                    had_sysctl = True
                netns.sysctl.apply(iface, do_apply)

        if netns.sysctl.has_globals():
            if not had_sysctl:
                logger.info("configure sysctl settings...")
                had_sysctl = True
            netns.sysctl.apply_globals(do_apply)

        return had_sysctl

    def _apply_iface(self, do_apply, netns, ifname, by_vrrp, vrrp_type, vrrp_name, vrrp_state):
        if ifname in netns.links:
            link = netns.links[ifname]

        # check for vrrp mode:
        #   disable: vrrp type & name matches, but vrrp state not
        #   ignore : vrrp type & name does not match
        if ifname in netns.vrrp['links']:
            # this is a vrrp link but not running in a vrrp action
            if not by_vrrp:
                return
            else:
                # skip if another vrrp type & name is addressed
                if not link.match_vrrp_select(vrrp_type, vrrp_name):
                    logger.log_ok("other vrrp")
                    return
                # vrrp type & name does match, but the state does not => disable this interface
                elif not vrrp_name in netns.vrrp[vrrp_type] or not vrrp_state in netns.vrrp[vrrp_type][vrrp_name] or not ifname in netns.vrrp[vrrp_type][vrrp_name][vrrp_state]:
                    if ifname in netns.links:
                        logger.debug('to be disabled due to vrrp constraint',
                                    extra={'iface': ifname})
                        link.settings['state'] = 'down'
        # ignore if this link is not vrrp aware at all
        elif by_vrrp:
            logger.log_ok("no vrrp")
            return

        if ifname in netns.links:
            excpts = link.apply(do_apply, netns.sysctl)
            if excpts.has_errno(errno.EEXIST):
                retry = True

        if ifname in netns.tc:
            netns.tc[ifname].apply(do_apply)

        if ifname in netns.xdp:
            netns.xdp[ifname].apply(do_apply, netns.bpf_progs)

        if ifname in netns.addresses and netns.addresses[ifname]:
            netns.addresses[ifname].apply(self.ipaddr_ignore, self.ignore.get(
                'ipaddr_dynamic', True), do_apply)

        if ifname in netns.fdb:
            netns.fdb[ifname].apply(do_apply)

        if ifname in netns.neighbours:
            netns.neighbours[ifname].apply(do_apply)

        if ifname in netns.wireguard:
            netns.wireguard[ifname].apply(do_apply)

    def _apply_routing(self, do_apply, netns, by_vrrp, vrrp_type, vrrp_name, vrrp_state):
        if not netns.tables is None:
            netns.tables.apply(self.ignore.get('routes', []), do_apply, by_vrrp, vrrp_type, vrrp_name, vrrp_state)

        if not netns.rules is None:
            netns.rules.apply(self.ignore.get('rules', []), do_apply, by_vrrp, vrrp_type, vrrp_name, vrrp_state)

    def show(self, showall=False):
        if showall:
            defaults = deepcopy(Parser._default_ifstates)
        else:
            defaults = {}

        ipaddr_ignore = []
        for ip in Parser._default_ifstates['ignore']['ipaddr_builtin']:
            ipaddr_ignore.append(ip_network(ip))

        root_config = self._show_netns(self.root_netns, showall, ipaddr_ignore)
        netns_instances = get_netns_instances()
        if len(netns_instances) > 0:
            netns_configs = {}
            for netns in netns_instances:
                netns_configs[netns.netns] = self._show_netns(netns, showall, ipaddr_ignore)

            return {**defaults, **root_config, 'namespaces': netns_configs}


        return {**defaults, **root_config}

    def _show_netns(self, netns, showall, ipaddr_ignore):
        ifs_links = []
        for ipr_link in netns.ipr.get_links():
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

                for addr in netns.ipr.get_addr(index=ipr_link['index']):
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
                    permaddr = netns.ipr.get_permaddr(name)
                    if not permaddr is None:
                        if addr is None:
                            ifs_link['link']['addr'] = permaddr
                        elif addr != permaddr:
                            ifs_link['link']['permaddr'] = permaddr
                    businfo = netns.ipr.get_businfo(name)
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
                            ifs_link['link'][attr] = netns.ipr.get_ifname_by_index(
                                ref)
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            logger.warning('lookup {} failed: {}'.format(
                                attr, err.args[1]), extra={'iface': name, 'netns': netns})
                            ifs_link['link'][attr] = ref

                mtu = ipr_link.get_attr('IFLA_MTU')
                if not mtu is None:
                    if not mtu in [1500, 65536] or name == 'lo':
                        ifs_link['link']['mtu'] = mtu

                brport.BRPort.show(netns.ipr, showall, ipr_link['index'], ifs_link)

                if name == 'lo':
                    if ifs_link['addresses'] == Parser._default_lo_link['addresses']:
                        del(ifs_link['addresses'])

                    if ifs_link['link'] == Parser._default_lo_link['link']:
                        del(ifs_link['link'])

                    if len(ifs_link) > 1:
                        ifs_links.append(ifs_link)
                else:
                    ifs_links.append(ifs_link)

        routing = {
            'routes': Tables(netns).show_routes(Parser._default_ifstates['ignore']['routes_builtin']),
            'rules': Rules(netns).show_rules(Parser._default_ifstates['ignore']['rules_builtin']),
        }

        return {**{'interfaces': ifs_links, 'routing': routing}}

    def get_defaults(self, **kwargs):
        for default in self.defaults:
            for match in default['match']:
                matching = True

                for option, regex in match.items():
                    if not option in kwargs:
                        matching = False
                    elif not re.match(regex, kwargs[option]):
                        matching = False

                if matching:
                    return default

        return {}

    def gen_unique_ifname(self):
        '''
        Get a random unique ifname over all namespaces and configured ifnames.
        '''
        while True:
            ifname = "ifs.tmp.{}".format(secrets.token_hex(3))
            item = self.link_registry.get_link(ifname=ifname)
            if item is None:
                return ifname
