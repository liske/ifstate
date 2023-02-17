from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import RouteDupblicate, netlinkerror_classes
from ipaddress import ip_address, ip_network, IPv6Network
from pyroute2.netlink.rtnl.fibmsg import FR_ACT_VALUES
from pyroute2.netlink.rtnl import rt_type
import collections.abc
from glob import glob
import os
import re
import sys
import socket
from socket import AF_INET, AF_INET6


def route_matches(r1, r2, fields=('dst', 'priority', 'proto'), indent=None):
    return _matches(r1, r2, fields, indent)


def rule_matches(r1, r2, fields=('priority', 'iif', 'oif', 'dst', 'metric', 'protocol'), indent=None):
    return _matches(r1, r2, fields, indent)


def _matches(r1, r2, fields, indent):
    for fld in fields:
        if not indent is None:
            logger.debug("{}: {} - {}".format(fld, r1.get(fld), r2.get(fld)), extra={'iface': indent})
        if fld in r1 and fld in r2:
            if r1[fld] != r2[fld]:
                return False
        elif fld in r1 or fld in r2:
            return False
    return True


class RTLookup():
    def __init__(self, name):
        self.name = name
        self.str2id = {}
        self.id2str = {}

        try:
            fn = os.path.join('/etc/iproute2', name)
            with open(fn, 'r') as fp:
                self._parse(fp)

            for fn in glob(os.path.join('/etc/iproute2', "{}.d".format(name), "*.conf")):
                with open(fn, 'r') as fp:
                    self._parse(fp)
        except:
            logger.info('could not open {}'.format(fn))

    def _parse(self, fp):
        for line in fp:
            m = re.search(r'^(\d+)\s+(\S+)$', line)
            if m:
                self.str2id[m.group(2)] = int(m.group(1))
                self.id2str[int(m.group(1))] = m.group(2)

    def lookup_id(self, key):
        if type(key) == int or key.isdecimal():
            return int(key)

        return self.str2id[key]

    def lookup_str(self, key):
        return self.id2str.get(key, key)


class RTLookups():
    tables = RTLookup('rt_tables')
    realms = RTLookup('rt_realms')
    scopes = RTLookup('rt_scopes')
    protos = RTLookup('rt_protos')
    group = RTLookup('group')

RT_LOOKUPS_DICT = {
    'table': RTLookups.tables,
    'scope': RTLookups.scopes,
    'proto': RTLookups.protos,
    'realm': RTLookups.realms,
}

RT_LOOKUPS_DEFAULTS = {
    'table': 254,
    'scope': 0,
    'proto': 3,
    'realm': 0,
    'tos': 0,
}

class Tables(collections.abc.Mapping):
    def __init__(self):
        self.tables = {
            254: [],
        }

    def __getitem__(self, key):
        if not key in self.tables:
            raise KeyError()

        return self.tables[key]

    def __iter__(self):
        return self.tables.__iter__()

    def __len__(self):
        return len(self.tables)

    def add(self, route):
        dst = ip_network(route['to'])
        rt = {
            'type': route.get('type', 'unicast'),
            'dst': dst.with_prefixlen,
        }

        for key, lookup in RT_LOOKUPS_DICT.items():
            try:
                rt[key] = route.get(key, RT_LOOKUPS_DEFAULTS[key])
                rt[key] = lookup.lookup_id(rt[key])
            except KeyError as err:
                # mapping not available - catch exception and skip it
                logger.warning('ignoring unknown %s "%s"', key, rt[key],
                               extra={'iface': rt['dst']})
                rt[key] = RT_LOOKUPS_DEFAULTS[key]

        if type(rt['type']) == str:
            rt['type'] = rt_type[rt['type']]

        if 'dev' in route:
            rt['oif'] = route['dev']

        if 'via' in route:
            rt['gateway'] = str(ip_address(route['via']))

        if 'src' in route:
            rt['prefsrc'] = route['src']

        if 'preference' in route:
            rt['priority'] = route['preference']
        elif isinstance(dst, IPv6Network):
            rt['priority'] = 1024
        else:
            rt['priority'] = 0

        if not rt['table'] in self.tables:
            self.tables[rt['table']] = []
        self.tables[rt['table']].append(rt)

    def show_routes(self, ignores):
        routes = []
        for route in ipr.get_routes(family=AF_INET) + ipr.get_routes(family=AF_INET6):
            # skip routes from local table
            table = route.get_attr('RTA_TABLE')
            if table == 255:
                continue

            # skip ignored routes
            ignore = False
            for iroute in ignores:
                if route_matches(route, iroute, iroute.keys()):
                    ignore = True
                    break
            if ignore:
                continue

            if route['dst_len'] > 0:
                dst = ip_network(
                    '{}/{}'.format(route.get_attr('RTA_DST'), route['dst_len'])).with_prefixlen
            elif route['family'] == AF_INET:
                dst = ip_network('0.0.0.0/0').with_prefixlen
            elif route['family'] == AF_INET6:
                dst = ip_network('::/0').with_prefixlen

            rt = {
                'to': dst,
            }

            if table != 254:
                rt['table'] = RTLookups.tables.lookup_str(table),

            dev = route.get_attr('RTA_OIF')
            if dev:
                link = next(iter(ipr.get_links(dev)), None)
                if link:
                    rt['dev'] = link.get_attr('IFLA_IFNAME', dev)
                else:
                    rt['dev'] = dev

            via = route.get_attr('RTA_GATEWAY')
            if via:
                rt['via'] = via

            realm = route.get_attr('RTA_FLOW')
            if realm:
                rt['realm'] = RTLookups.realms.lookup_str(realm)

            if route['scope'] != 0:
                rt['scope'] = RTLookups.scopes.lookup_str(route['scope'])

            if route['proto'] != 3:
                rt['proto'] = RTLookups.protos.lookup_str(route['proto'])

            if route['tos'] != 0:
                rt['tos'] = route['tos']

            src = route.get_attr('RTA_PREFSRC')
            if src:
                rt['src'] = src

            rtype = route['type']
            if rtype != 1:
                rt['type'] = rt_type[rtype]

            priority = route.get_attr('RTA_PRIORITY')
            if priority:
                rt['preference'] = priority

            routes.append(rt)

        return routes

    def kernel_routes(self, table):
        routes = []
        for route in ipr.get_routes(table=table, family=AF_INET) + ipr.get_routes(table=table, family=AF_INET6):
            # ignore RTM_F_CLONED routes
            if route['flags'] & 512:
                continue

            if route['dst_len'] > 0:
                dst = ip_network(
                    '{}/{}'.format(route.get_attr('RTA_DST'), route['dst_len'])).with_prefixlen
            elif route['family'] == AF_INET:
                dst = ip_network('0.0.0.0/0').with_prefixlen
            elif route['family'] == AF_INET6:
                dst = ip_network('::/0').with_prefixlen

            rt = {
                'table': route.get_attr('RTA_TABLE'),
                'type': route['type'],
                'dst': dst,
                'oif': route.get_attr('RTA_OIF'),
                'scope': route['scope'],
                'proto': route['proto'],
                'realm': route.get_attr('RTA_FLOW', 0),
                'tos': route['tos'],
                'priority': 0
            }

            gateway = route.get_attr('RTA_GATEWAY')
            if not gateway is None:
                rt['gateway'] = str(ip_address(gateway))

            metric = route.get_attr('RTA_PRIORITY')
            if not metric is None:
                rt['metric'] = metric

            pref = route.get_attr('RTA_PREF')
            if not pref is None:
                rt['pref'] = pref

            prefsrc = route.get_attr('RTA_PREFSRC')
            if not prefsrc is None:
                rt['prefsrc'] = prefsrc

            priority = route.get_attr('RTA_PRIORITY')
            if not priority is None:
                rt['priority'] = priority

            routes.append(rt)
        return routes

    def apply(self, ignores, do_apply):
        for table, croutes in self.tables.items():
            pfx = RTLookups.tables.lookup_str(table)
            logger.info('\nconfiguring routing table {}...'.format(pfx))

            kroutes = self.kernel_routes(table)

            for route in croutes:
                if 'oif' in route and type(route['oif']) == str:
                    route['oif'] = next(
                        iter(ipr.link_lookup(ifname=route['oif'])), None)
                found = False
                identical = False
                for i, kroute in enumerate(kroutes):
                    if route_matches(route, kroute):
                        del kroutes[i]
                        found = True
                        if route_matches(route, kroute, route.keys(), indent=route['dst']):
                            identical = True
                            break

                if identical:
                    logger.info(
                        'ok', extra={'iface': route['dst'], 'style': IfStateLogging.STYLE_OK})
                else:
                    if found:
                        logger.info('change', extra={
                                    'iface': route['dst'], 'style': IfStateLogging.STYLE_CHG})
                    else:
                        logger.info(
                            'add', extra={'iface': route['dst'], 'style': IfStateLogging.STYLE_CHG})

                    logger.debug("ip route replace: {}".format(
                        " ".join("{}={}".format(k, v) for k, v in route.items())))
                    try:
                        if do_apply:
                            ipr.route('replace', **route)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('route setup {} failed: {}'.format(
                            route['dst'], err.args[1]))

            for route in kroutes:
                ignore = False
                for iroute in ignores:
                    if route_matches(route, iroute, iroute.keys()):
                        ignore = True
                        break
                if ignore:
                    continue

                logger.info(
                    'del', extra={'iface': route['dst'], 'style': IfStateLogging.STYLE_DEL})
                try:
                    if do_apply:
                        ipr.route('del', **route)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('removing route {} failed: {}'.format(
                        route['dst'], err.args[1]))


class Rules():
    def __init__(self):
        self.rules = []

    def add(self, rule):
        ru = {
            'table': RTLookups.tables.lookup_id(rule.get('table', 254)),
            'protocol': RTLookups.protos.lookup_id(rule.get('proto', 0)),
            'tos': rule.get('tos', 0),
        }

        if 'action' in rule and type(rule['action']) == str:
            ru['action'] = {
                "to_tbl": "FR_ACT_TO_TBL",
                "unicast": "FR_ACT_UNICAST",
                "blackhole": "FR_ACT_BLACKHOLE",
                "unreachable": "FR_ACT_UNREACHABLE",
                "prohibit": "FR_ACT_PROHIBIT",
                "nat": "FR_ACT_NAT",
            }.get(rule['action'], rule['action'])
        else:
            ru['action'] = rule.get('action'.lower(), "FR_ACT_TO_TBL")

        if 'fwmark' in rule:
            ru['fwmark'] = rule['fwmark']

        if 'ipproto' in rule:
            if type(rule['ipproto']) == str:
                ru['ip_proto'] = socket.getprotobyname(rule['ipproto'])
            else:
                ru['ip_proto'] = rule['ipproto']

        if 'to' in rule:
            ru['dst'] = str(ip_network(rule['to']).network_address)
            ru['dst_len'] = ip_network(rule['to']).prefixlen

        if 'from' in rule:
            ru['src'] = str(ip_network(rule['from']).network_address)
            ru['src_len'] = ip_network(rule['from']).prefixlen

        if 'iif' in rule:
            ru['iifname'] = rule['iif']

        if 'oif' in rule:
            ru['oifname'] = rule['oif']

        if 'priority' in rule:
            ru['priority'] = rule['priority']

        self.rules.append(ru)

    def kernel_rules(self):
        rules = []
        for rule in ipr.get_rules(family=AF_INET) + ipr.get_rules(family=AF_INET6):
            ru = {
                'action': FR_ACT_VALUES.get(rule['action']),
                'table': rule.get_attr('FRA_TABLE'),
                'protocol': rule.get_attr('FRA_PROTOCOL'),
                'priority': rule.get_attr('FRA_PRIORITY', 0),
                'family': rule['family'],
                'tos': rule['tos'],
            }

            if rule['dst_len'] > 0:
                ru['dst'] = rule.get_attr('FRA_DST')
                ru['dst_len'] = rule['dst_len']

            if rule['src_len'] > 0:
                ru['src'] = rule.get_attr('FRA_SRC')
                ru['src_len'] = rule['src_len']

            for field in ['iifname', 'oifname', 'fwmark', 'ip_proto']:
                value = rule.get_attr('FRA_{}'.format(field.upper()))
                if not value is None:
                    ru[field] = value

            rules.append(ru)
        return rules

    def show_rules(self, ignores):
        rules = []
        for rule in self.kernel_rules():
            # skip ignored routes
            ignore = False
            for irule in ignores:
                if 'proto' in irule:
                    irule['protocol'] = irule['proto']
                    del irule['proto']
                if rule_matches(rule, irule, irule.keys()):
                    ignore = True
                    break
            if ignore:
                continue

            rule['action'] = {
                "FR_ACT_TO_TBL": "to_tbl",
                "FR_ACT_UNICAST": "unicast",
                "FR_ACT_BLACKHOLE": "blackhole",
                "FR_ACT_UNREACHABLE": "unreachable",
                "FR_ACT_PROHIBIT": "prohibit",
                "FR_ACT_NAT": "nat",
            }.get(rule['action'], rule['action'])

            if rule['action'] == "to_tbl":
                del rule['action']

            if 'protocol' in rule and rule['protocol'] > 0:
                rule['proto'] = rule['protocol']
                del rule['protocol']

            if 'src_len' in rule and rule['src_len'] > 0:
                rule['from'] = ip_network(
                    '{}/{}'.format(rule['src'], rule['src_len'])).with_prefixlen

            for key in ['src', 'src_len', 'tos', 'protocol']:
                if key in rule:
                    del rule[key]

            rules.append(rule)

        return rules

    def apply(self, ignores, do_apply):
        logger.info('\nconfiguring routing rules...')
        krules = self.kernel_rules()
        for rule in self.rules:
            found = False
            for i, krule in enumerate(krules):
                if rule_matches(rule, krule, rule.keys()):
                    del krules[i]
                    found = True
                    break

            if found:
                logger.info(
                    'ok', extra={'iface': '#{}'.format(rule['priority']), 'style': IfStateLogging.STYLE_OK})
            else:
                logger.info(
                    'add', extra={'iface': '#{}'.format(rule['priority']), 'style': IfStateLogging.STYLE_CHG})

                logger.debug("ip rule add: {}".format(
                    " ".join("{}={}".format(k, v) for k, v in rule.items())))
                try:
                    if do_apply:
                        ipr.rule('add', **rule)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('rule setup failed: {}'.format(err.args[1]))

        for rule in krules:
            ignore = False
            for irule in ignores:
                if 'proto' in irule:
                    irule['protocol'] = irule['proto']
                    del irule['proto']
                if rule_matches(rule, irule, irule.keys()):
                    ignore = True
                    break
            if ignore:
                continue

            logger.info(
                'del', extra={'iface': '#{}'.format(rule['priority']), 'style': IfStateLogging.STYLE_DEL})
            try:
                if do_apply:
                    ipr.rule('del', **rule)
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                logger.warning('removing rule failed: {}'.format(err.args[1]))
