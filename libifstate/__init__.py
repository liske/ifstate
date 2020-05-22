from libifstate.exception import LinkDuplicate
from libifstate.link.base import Link
from libifstate.parser import Parser
from libifstate.util import logger, ipr
import re

class IfState():
    def __init__(self):
        self.links = {}
        self.ignore = set([])
    
    def update(self, ifstates):
        # add interfaces from config
        for ifstate in ifstates['interfaces']:
            name = ifstate['name']
            if name in self.links:
                raise LinkDuplicate()
            if 'link' in ifstate:
                self.links[name] = Link(name, **ifstate['link'])

        # add ignore list items
        self.ignore.update(ifstates['ignore'])

    def commit(self):
        commited = []
        while len(commited) < len(self.links):
            last = len(commited)
            for name, link in self.links.items():
                dep = link.depends()
                if dep is None or dep in commited:
                    link.commit()
                    commited.append(name)
            if last == len(commited):
                raise LinkCircularLinked()

        for link in ipr.get_links():
            name = link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not name in self.links and not any(re.match(regex, name) for regex in self.ignore):
                info = link.get_attr('IFLA_LINKINFO')
                # remove virtual interface
                if info is not None:
                    kind = info.get_attr('IFLA_INFO_KIND')
                    logger.info('%s is a orphan %s interface => remove', name, kind or 'virtual')
                    ipr.link('set', index=link.get('index'), state='down')
                    ipr.link('del', index=link.get('index'))
                # shutdown physical interfaces
                else:
                    if link.get('state') == 'down':
                        logger.warning('%s is a orphan physical interface', name)
                    else:
                        logger.warning('%s is a orphan physical interface => shutdown', name)
                        ipr.link('set', index=link.get('index'), state='down')

    def describe(self):
        ifs_links = []
        for ipr_link in ipr.get_links():
            name = ipr_link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not any(re.match(regex, name) for regex in Parser._default_ifstates['ignore']):
                kind = 'physical'

                ifs_link = {
                        'name': name,
                        'link': {
                            'state': ipr_link['state'],
                        },
                }

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

        return {
            'interfaces': ifs_links,
        }
