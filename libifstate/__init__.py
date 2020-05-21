from libifstate.exception import LinkDuplicate
from libifstate.link import Link
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
            name = ifstate.pop('name')
            if name in self.links:
                raise LinkDuplicate()
            self.links[name] = Link(name, **ifstate)

        # add ignore list items
        self.ignore.update(ifstates['ignore'])

    def commit(self):
        last = 0
        commited = []
        while len(commited) < len(self.links):
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
                    ipr.link('del', index=link.get('index'))
                # shutdown physical interfaces
                else:
                    if link.get('state') == 'down':
                        logger.warning('%s is a orphan physical interface', name)
                    else:
                        logger.warning('%s is a orphan physical interface => shutdown', name)
                        ipr.link('set', index=link.get('index'), state='down')

    def template(self):
        ifs_links = []
        for ipr_link in ipr.get_links():
            name = ipr_link.get_attr('IFLA_IFNAME')
            # skip links on ignore list
            if not any(re.match(regex, name) for regex in Parser._default_ifstates['ignore']):
                kind = 'physical'

                info = ipr_link.get_attr('IFLA_LINKINFO')
                if info is not None:
                    kind = info.get_attr('IFLA_INFO_KIND')

                ifs_link = {
                        'ifname': name,
                        'kind': kind,
                }

                # cname = "{}Link".format(kind.lower().capitalize())
                # for c in Link.__subclasses__():
                #     if c.__name__ == cname:

                ifs_links.append(ifs_link)

        return {
            'interfaces': ifs_links,
        }
