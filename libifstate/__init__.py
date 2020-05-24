from libifstate.exception import LinkDuplicate
from libifstate.link.base import Link
from libifstate.address import Addresses
from libifstate.parser import Parser
from libifstate.util import logger, ipr
from ipaddress import ip_network, ip_interface
import re

__version__ = "0.3"

class IfState():
    def __init__(self):
        self.links = {}
        self.addresses = {}
        self.ignore = {}
    
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

            if 'address' in ifstate:
                self.addresses[name] = Addresses(name, ifstate['address'])
            else:
                self.addresses[name] = None

        # add ignore list items
        self.ignore.update(ifstates['ignore'])

    def commit(self):
        self.ipaddr_ignore = set()
        for ip in self.ignore.get('ipaddr', []):
            self.ipaddr_ignore.add( ip_network(ip) )

        logger.info('configuring interface links')

        commited = []
        while len(commited) < len(self.links):
            last = len(commited)
            for name, link in self.links.items():
                if link is None:
                    logger.debug('skipped due to no link settings', extra={'iface': name})
                    commited.append(name)
                else:
                    dep = link.depends()
                    if dep is None or dep in commited:
                        link.commit()
                        commited.append(name)
            if last == len(commited):
                raise LinkCircularLinked()

        for link in ipr.get_links():
            name = link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not name in self.links and not any(re.match(regex, name) for regex in self.ignore.get('ifname', [])):
                info = link.get_attr('IFLA_LINKINFO')
                # remove virtual interface
                if info is not None:
                    kind = info.get_attr('IFLA_INFO_KIND')
                    logger.info('orphan %s interface, removing', kind or 'virtual', extra={'iface': name})
                    ipr.link('set', index=link.get('index'), state='down')
                    ipr.link('del', index=link.get('index'))
                # shutdown physical interfaces
                else:
                    if link.get('state') == 'down':
                        logger.warning('is an orphan physical interface', extra={'iface': name})
                    else:
                        logger.warning('is an orphan physical interface, shutting down', extra={'iface': name})
                        ipr.link('set', index=link.get('index'), state='down')

        logger.info('configuring interface ip addresses')
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
                addresses.commit(self.ipaddr_ignore)

    def describe(self):
        self.ipaddr_ignore = set()
        for ip in Parser._default_ifstates.get('ignore').get('ipaddr'):
            self.ipaddr_ignore.add( ip_network(ip) )

        ifs_links = []
        for ipr_link in ipr.get_links():
            name = ipr_link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not any(re.match(regex, name) for regex in Parser._default_ifstates['ignore'].get('ifname', [])):
                kind = 'physical'

                ifs_link = {
                        'name': name,
                        'addr': [],
                        'link': {
                            'state': ipr_link['state'],
                        },
                }

                for addr in ipr.get_addr(index=ipr_link['index']):
                    ip = ip_interface(addr.get_attr('IFA_ADDRESS') + '/' + str(addr['prefixlen']))
                    if not any(ip in net for net in self.ipaddr_ignore):
                        ifs_link['addr'].append(ip.with_prefixlen)

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
                    ifs_link['link']['kind'] = kind

                ifs_links.append(ifs_link)

        return { **Parser._default_ifstates, **{'interfaces': ifs_links}}
