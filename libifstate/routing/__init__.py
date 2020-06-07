from libifstate.util import logger, ipr, LogStyle
from libifstate.exception import RouteDupblicate
from ipaddress import ip_address, ip_network
from pyroute2.netlink.exceptions import NetlinkError
import collections.abc
from glob import glob
import os
import re
import sys
from socket import AF_INET, AF_INET6

def route_matches(r1, r2, fields=('dst', 'metric', 'proto'), verbose=False):
    for fld in fields:
        if verbose:
            logger.debug("{}: {} - {}".format(fld, r1.get(fld), r2.get(fld)))
        if fld in r1 and fld in r2:
            if r1[fld] != r2[fld]:
                return False
        elif fld in r1 or fld in r2:
                return False
    return True

def route_identical(r1, r2):
    return route_matches(r1, r2, set(r1.keys()) | set(r2.keys()), True)

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
        rt = {
            'table': RTLookups.tables.lookup_id( route.get('table', 254) ),
            'dst': ip_network(route['to']).with_prefixlen,
            'scope': RTLookups.scopes.lookup_id(route.get('scope', 0)),
            'proto': RTLookups.protos.lookup_id(route.get('proto', 3)),
            'realm': RTLookups.realms.lookup_id(route.get('realm', 0)),
            'tos': route.get('tos', 0),
        }

        if 'dev' in route:
            rt['oif'] = next(iter(ipr.link_lookup(ifname=route['dev'])))

        if 'via' in route:
            rt['gateway'] = str(ip_address(route['via']))

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
            if route['proto'] in ignores.get('protos', []):
                continue

            if route['dst_len'] > 0:
                dst = ip_network('{}/{}'.format(route.get_attr('RTA_DST'), route['dst_len'])).with_prefixlen
            elif route['family']==AF_INET:
                dst = ip_network('0.0.0.0/0').with_prefixlen
            elif route['family']==AF_INET6:
                dst = ip_network('::/0').with_prefixlen

            rt = {
                'to': dst,
                'table': RTLookups.tables.lookup_str(table),
            }

            dev = route.get_attr('RTA_OIF')
            if dev:
                link = next(iter(ipr.get_links(dev)), None)
                if link:
                    rt['dev'] = link.get_attr('IFLA_IFNAME', dev)
                else:
                    rt['dev'] = dev

            realm = route.get_attr('RTA_FLOW')
            if realm:
                rt['realm'] = RTLookups.realms.lookup_str(realm)

            if route['scope'] != 0:
                rt['scope'] = RTLookups.scopes.lookup_str(route['scope'])

            if route['proto'] != 3:
                rt['proto'] = RTLookups.protos.lookup_str(route['proto'])

            if route['tos'] != 0:
                rt['tos'] = route['tos']

            routes.append(rt)

        return routes

    def kernel_routes(self, table):
        routes = []
        for route in ipr.get_routes(table=table, family=AF_INET) + ipr.get_routes(table=table, family=AF_INET6):
            if route['dst_len'] > 0:
                dst = ip_network('{}/{}'.format(route.get_attr('RTA_DST'), route['dst_len'])).with_prefixlen
            elif route['family']==AF_INET:
                dst = ip_network('0.0.0.0/0').with_prefixlen
            elif route['family']==AF_INET6:
                dst = ip_network('::/0').with_prefixlen

            rt = {
                'table': route.get_attr('RTA_TABLE'),
                'dst': dst,
                'oif': route.get_attr('RTA_OIF'),
                'scope': route['scope'],
                'proto': route['proto'],
                'realm': route.get_attr('RTA_FLOW', 0),
                'tos': route['tos'],
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

            routes.append(rt)
        return routes

    def apply(self, ignores):
        for table, croutes in self.tables.items():
            pfx = RTLookups.tables.lookup_str(table)
            logger.info('\nconfiguring routing table {}...'.format(pfx))

            kroutes = self.kernel_routes(table)

            for route in croutes:
                found = False
                identical = False
                for i, kroute in enumerate(kroutes):
                    if route_matches(route, kroute):
                        del kroutes[i]
                        found = True
                        if route_identical(route, kroute):
                            identical = True
                            break

                if identical:
                    logger.info('ok', extra={'iface': route['dst'], 'style': LogStyle.OK})
                else:
                    if found:
                        logger.info('change', extra={'iface': route['dst'], 'style': LogStyle.CHG})
                    else:
                        logger.info('add', extra={'iface': route['dst'], 'style': LogStyle.CHG})

                    logger.debug("ip route replace: {}".format( " ".join("{}={}".format(k, v) for k,v in route.items()) ))
                    try:
                        ipr.route('replace', **route)
                    except NetlinkError as err:
                        logger.warning('setup route {} failed: {}'.format(route['dst'], err.args[1]))

            for route in kroutes:
                if route['proto'] in ignores.get('protos', []):
                    continue

                logger.info('del', extra={'iface': route['dst'], 'style': LogStyle.DEL})
                ipr.route('del', **route)


class Routes():
    def __init__(self):
        self.routes = {}

    def add(self, route):
        dst = ip_network(route['dst'])
        if dst in self.routes:
            raise RouteDupblicate()

        if 'table' in route:
            route['table'] = RTLookups.tables.lookup_id(route.get_attr('RTA_TABLE', 'main'))
        # if 'dev' in route:
        #     route['dev'] = xxxx
        if 'scope' in route:
            route['scope'] = RTLookups.scopes.lookup_id(route['scope'])

        if 'proto' in route:
            route['proto'] = RTLookups.protos.lookup_id(route['proto'])

        if 'gateway' in route:
            route['gateway'] = ip_address(route['gateway'])

        if 'realm' in route:
            route['realm'] = RTLookups.realms.lookup_id(route['realm'])

        self.routes[dst] = route


class Rules():

    def add(self, rule):
        pass

    def apply(self, ignores):
        pass
