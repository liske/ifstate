from libifstate.exception import LinkDuplicate
from libifstate.link.base import Link
from libifstate.address import Addresses
from libifstate.routing import Tables, Rules
from libifstate.sysctl import Sysctl
from libifstate.parser import Parser
from libifstate.util import logger, ipr, LogStyle
from libifstate.exception import LinkCircularLinked, LinkNoConfigFound, NetlinkError, ParserValidationError
from ipaddress import ip_network, ip_interface
from jsonschema import validate, ValidationError
import pkgutil
import re
import json

__version__ = "0.7.2"


class IfState():
    def __init__(self):
        logger.debug('IfState {}'.format(__version__))
        self.links = {}
        self.addresses = {}
        self.ignore = {}
        self.tables = None
        self.rules = None
        self.sysctl = Sysctl()

    def update(self, ifstates):
        # check config schema
        schema = json.loads(pkgutil.get_data(
            "libifstate", "../schema/ifstate.conf.schema.json"))
        try:
            validate(ifstates, schema)
        except ValidationError as ex:
            if len(ex.path) > 0:
                path = ["$"]
                for i, p in enumerate(ex.path):
                    if type(p) == int:
                        path.append("[{}]".format(p))
                    else:
                        path.append(".")
                        path.append(p)

                detail = "{}: {}".format("".join(path), ex.message)
            else:
                detail = ex.message
            raise ParserValidationError(detail)

        # parse options
        if 'options' in ifstates:
            # parse global sysctl settings
            if 'sysctl' in ifstates['options']:
                for iface in ['all', 'default']:
                    if iface in ifstates['options']['sysctl']:
                        self.sysctl.add(
                            iface, ifstates['options']['sysctl'][iface])

        # add interfaces from config
        for ifstate in ifstates['interfaces']:
            name = ifstate['name']
            if name in self.links:
                raise LinkDuplicate()
            if 'link' in ifstate:
                self.links[name] = Link(name, ifstate['link'], ifstate.get('ethtool'))
            else:
                self.links[name] = None

            if 'addresses' in ifstate:
                self.addresses[name] = Addresses(name, ifstate['addresses'])
            else:
                self.addresses[name] = None

            if 'sysctl' in ifstate:
                self.sysctl.add(name, ifstate['sysctl'])

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
        self._apply(True)

    def check(self):
        self._apply(False)

    def _apply(self, do_apply):
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

        logger.info("\nconfiguring interface links")

        applied = []
        while len(applied) < len(self.links):
            last = len(applied)
            for name, link in self.links.items():
                if link is None:
                    logger.debug('skipped due to no link settings',
                                 extra={'iface': name})
                    applied.append(name)
                else:
                    dep = link.depends()
                    if dep is None or dep in applied:
                        self.sysctl.apply(name, do_apply)
                        link.apply(do_apply)
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
                        'del', extra={'iface': name, 'style': LogStyle.DEL})
                    if do_apply:
                        try:
                            ipr.link('set', index=link.get('index'), state='down')
                            ipr.link('del', index=link.get('index'))
                        except NetlinkError as err:
                            logger.warning('removing link {} failed: {}'.format(
                                name, err.args[1]))
                # shutdown physical interfaces
                else:
                    if link.get('state') == 'down':
                        logger.warning('orphan', extra={
                                       'iface': name, 'style': LogStyle.OK})
                    else:
                        logger.warning('orphan', extra={
                                       'iface': name, 'style': LogStyle.CHG})
                        if do_apply:
                            try:
                                ipr.link('set', index=link.get('index'), state='down')
                            except NetlinkError as err:
                                logger.warning('updating link {} failed: {}'.format(
                                    name, err.args[1]))

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
                    logger.debug('skipped due to no address settings', extra={
                                 'iface': name})
                else:
                    addresses.apply(self.ipaddr_ignore, do_apply)
        else:
            logger.info("\nno interface ip addressing to be applied")

        if not self.tables is None:
            self.tables.apply(self.ignore.get('routes', []), do_apply)

        if not self.rules is None:
            self.rules.apply(self.ignore.get('rules', []), do_apply)

    def show(self):
        self.ipaddr_ignore = set()
        for ip in Parser._default_ifstates.get('ignore').get('ipaddr'):
            self.ipaddr_ignore.add(ip_network(ip))

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
                    ip = ip_interface(addr.get_attr(
                        'IFA_ADDRESS') + '/' + str(addr['prefixlen']))
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

        return {**Parser._default_ifstates, **{'interfaces': ifs_links, 'routing': routing}}
