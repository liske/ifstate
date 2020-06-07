from libifstate.exception import LinkDuplicate
from libifstate.link.base import Link
from libifstate.address import Addresses
from libifstate.routing import Tables, Rules
from libifstate.parser import Parser
from libifstate.util import logger, ipr, LogStyle
from libifstate.exception import LinkCircularLinked, LinkNoConfigFound
from ipaddress import ip_network, ip_interface
import re

__version__ = "0.6.0"

class IfState():
    def __init__(self):
        self.links = {}
        self.addresses = {}
        self.ignore = {}
        self.tables = None
        self.rules = None
    
    def update(self, ifstates):
        # add interfaces from config
        for ifstate in ifstates['interfaces']:
            name = ifstate['name']
            if name in self.links:
                raise LinkDuplicate()
            if 'link' in ifstate:
                self.links[name] = Link(name, **ifstate['link'])
            else:
                self.links[name] = None

            if 'addresses' in ifstate:
                self.addresses[name] = Addresses(name, ifstate['addresses'])
            else:
                self.addresses[name] = None

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

    def apply(self):
        self.ipaddr_ignore = set()
        for ip in self.ignore.get('ipaddr', []):
            self.ipaddr_ignore.add( ip_network(ip) )

        if not any(not x is None for x in self.links.values()):
            logger.error("DANGER: Not a single link config has been found!")
            raise LinkNoConfigFound()

        logger.info('configuring interface links')

        applied = []
        while len(applied) < len(self.links):
            last = len(applied)
            for name, link in self.links.items():
                if link is None:
                    logger.debug('skipped due to no link settings', extra={'iface': name})
                    applied.append(name)
                else:
                    dep = link.depends()
                    if dep is None or dep in applied:
                        link.apply()
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
                    logger.info('del', extra={'iface': name, 'style': LogStyle.DEL})
                    ipr.link('set', index=link.get('index'), state='down')
                    ipr.link('del', index=link.get('index'))
                # shutdown physical interfaces
                else:
                    if link.get('state') == 'down':
                        logger.warning('orphan', extra={'iface': name, 'style': LogStyle.OK})
                    else:
                        logger.warning('orphan', extra={'iface': name, 'style': LogStyle.CHG})
                        ipr.link('set', index=link.get('index'), state='down')

        if any(not x is None for x in self.addresses.values()):
            logger.info("\nconfiguring interface ip addresses...")
            # add empty objects for unhandled interfaces
            for link in ipr.get_links():
                name = link.get_attr('IFLA_IFNAME')
                # skip links on ignore list
                if not name in self.addresses and not any(re.match(regex, name) for regex in self.ignore.get('ifname', [])):
                    self.addresses[name] = Addresses(name, [])

            for name, addresses in self.addresses.items():
                if addresses is None:
                    logger.debug('skipped due to no address settings', extra={'iface': name})
                else:
                    addresses.apply(self.ipaddr_ignore)
        else:
            logger.info("\nno interface ip addressing to be applied")

        if not self.tables is None:
            self.tables.apply(self.ignore.get('routes', []))

        if not self.rules is None:
            self.rules.apply(self.ignore.get('rules', []))

    def show(self):
        self.ipaddr_ignore = set()
        for ip in Parser._default_ifstates.get('ignore').get('ipaddr'):
            self.ipaddr_ignore.add( ip_network(ip) )

        ifs_links = []
        for ipr_link in ipr.get_links():
            name = ipr_link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not any(re.match(regex, name) for regex in Parser._default_ifstates['ignore'].get('ifname', [])):
                ifs_link = {
                        'name': name,
                        'addresses': [],
                        'link': {
                            'state': ipr_link['state'],
                        },
                }

                for addr in ipr.get_addr(index=ipr_link['index']):
                    ip = ip_interface(addr.get_attr('IFA_ADDRESS') + '/' + str(addr['prefixlen']))
                    if not any(ip in net for net in self.ipaddr_ignore):
                        ifs_link['addresses'].append(ip.with_prefixlen)

                info = ipr_link.get_attr('IFLA_LINKINFO')
                if info is not None:
                    kind = info.get_attr('IFLA_INFO_KIND')
                    ifs_link['link']['kind'] = kind

                    data = info.get_attr('IFLA_INFO_DATA')
                    # unsupported link type, fallback to raw encoding
                    if type(data) == str:
                        ifs_link['link']["info_data"] = data
                    elif data is not None:
                        for k, v in data['attrs']:
                            ifs_link['link'][ipr_link.nla2name(k)] = v
                else:
                    ifs_link['link']['kind'] = 'physical'
                    addr = ipr_link.get_attr('IFLA_ADDRESS')
                    if not addr is None:
                        ifs_link['link']['address'] = addr

                ifs_links.append(ifs_link)

        routing = {
            'routes': Tables().show_routes(Parser._default_ifstates['ignore']['routes']),
        }

        return { **Parser._default_ifstates, **{'interfaces': ifs_links, 'routing': routing}}
