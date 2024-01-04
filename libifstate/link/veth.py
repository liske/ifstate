from libifstate.util import logger
from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

class VethLink(Link):
    def __init__(self, ifstate, netns, name, link, ethtool, vrrp, brport):
        # use the bind_netns implementation to create the peer in the
        # target netns
        if 'peer_netns' in link:
            link['bind_netns'] = link['peer_netns']
            del(link['peer_netns'])

        super().__init__(ifstate, netns, name, link, ethtool, vrrp, brport)

    def create(self, do_apply, sysctl, excpts, oper="add"):
        '''
        Update the link registry for the created peer interface, too.
        '''
        result = super().create(do_apply, sysctl, excpts, oper)

        bind_netns = self.get_bind_netns()
        peer_link = next(iter(bind_netns.ipr.get_links(ifname=self.settings['peer'])), None)
        self.ifstate.link_registry.add_link(bind_netns, peer_link)

        return result

    def get_if_attr(self, key):
        '''
        Quirk to convert the 'peer' attribute from a ifindex value
        to the real ifname (netns aware).
        '''
        if key != "peer":
            return super().get_if_attr(key)

        peer = super().get_if_attr("link")

        if peer is None:
            return None

        bind_netns = self.get_bind_netns()
        lnk = next(iter(bind_netns.ipr.get_links(peer)), None)
        return lnk.get_attr("IFLA_IFNAME")

    def set_bind_state(self, state):
        '''
        Set the bind state for the peer, too.
        '''
        super().set_bind_state(state)

        bind_netns = self.get_bind_netns()
        peer_link = next(iter(bind_netns.ipr.get_links(ifname=self.settings['peer'])), None)

        fn = self.get_bind_fn(bind_netns.netns, peer_link['index'])
        try:
            with open(fn, 'wb') as fh:
                fh.write(self.netns.mount)
        except IOError as err:
            logger.warning('failed write `{}`: {}'.format(fn, err.args[1]))
