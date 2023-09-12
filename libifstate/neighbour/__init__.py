from libifstate.util import logger, IfStateLogging
from libifstate.exception import netlinkerror_classes
from ipaddress import ip_address


class Neighbours():
    def __init__(self, netns, iface, neighbours):
        self.netns = netns
        self.iface = iface
        self.neighbours = {}
        for neigh in neighbours:
            self.neighbours[ip_address(neigh['dst'])] = neigh.get('lladdr')

    def apply(self, do_apply):
        logger.debug('getting neighbours', extra={'iface': self.iface})

        # get ifindex
        idx = next(iter(self.netns.ipr.link_lookup(ifname=self.iface)), None)

        if idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get neighbour entries (only NUD_PERMANENT)
        ipr_neigh = {}
        neigh_add = {}
        for neigh in self.netns.ipr.get_neighbours(ifindex=idx, state=128):
            ip = ip_address(neigh.get_attr('NDA_DST'))
            ipr_neigh[ip] = neigh.get_attr('NDA_LLADDR')

        for ip, lladdr in self.neighbours.items():
            if ip in ipr_neigh and lladdr == ipr_neigh[ip]:
                logger.log_ok('neighbours', '= {}'.format(ip))
                del ipr_neigh[ip]
            else:
                neigh_add[ip] = lladdr

        for ip, lladdr in ipr_neigh.items():
            logger.log_del('neighbours', '- {}'.format(str(ip)))
            try:
                if do_apply:
                    self.netns.ipr.neigh("del", ifindex=idx, dst=str(
                        ip))
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                logger.warning('removing neighbour {} failed: {}'.format(
                    str(ip), err.args[1]))

        for ip, lladdr in neigh_add.items():
            logger.log_add('neighbours', '+ {}'.format(str(ip)))
            if do_apply:
                try:
                    opts = {
                        'ifindex': idx,
                        'dst': str(ip),
                        'lladdr': lladdr,
                        'state': 128
                    }

                    self.netns.ipr.neigh('replace', **opts)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('adding neighbour {} failed: {}'.format(
                        str(ip), err.args[1]))
