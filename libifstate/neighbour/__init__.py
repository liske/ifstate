from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import netlinkerror_classes
from ipaddress import ip_address


class Neighbours():
    def __init__(self, iface, neighbours):
        self.iface = iface
        self.neighbours = {}
        for neigh in neighbours:
            self.neighbours[ip_address(neigh['dst'])] = neigh.get('lladdr')

    def apply(self, do_apply):
        logger.debug('getting neighbours', extra={'iface': self.iface})

        # get ifindex
        idx = next(iter(ipr.link_lookup(ifname=self.iface)), None)

        if idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get neighbour entries (only NUD_PERMANENT)
        ipr_neigh = {}
        neigh_add = {}
        for neigh in ipr.get_neighbours(ifindex=idx, state=128):
            ip = ip_address(neigh.get_attr('NDA_DST'))
            ipr_neigh[ip] = neigh.get_attr('NDA_LLADDR')

        for ip, lladdr in self.neighbours.items():
            if ip in ipr_neigh and lladdr == ipr_neigh[ip]:
                logger.info(' %s', ip, extra={
                            'iface': self.iface, 'style': IfStateLogging.STYLE_OK})
                del ipr_neigh[ip]
            else:
                neigh_add[ip] = lladdr

        for ip, lladdr in ipr_neigh.items():
            logger.info(
                '-%s', str(ip), extra={'iface': self.iface, 'style': IfStateLogging.STYLE_DEL})
            try:
                if do_apply:
                    ipr.neigh("del", ifindex=idx, dst=str(
                        ip))
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                logger.warning('removing neighbour {} failed: {}'.format(
                    str(ip), err.args[1]))

        for ip, lladdr in neigh_add.items():
            logger.info('+%s', str(ip),
                        extra={'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
            if do_apply:
                try:
                    opts = {
                        'ifindex': idx,
                        'dst': str(ip),
                        'lladdr': lladdr,
                        'state': 128
                    }

                    ipr.neigh('replace', **opts)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('adding neighbour {} failed: {}'.format(
                        str(ip), err.args[1]))
