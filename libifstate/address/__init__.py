from libifstate.util import logger, ipr, IfStateLogging
from ipaddress import ip_interface
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_PERMANENT

class Addresses():
    def __init__(self, iface, addresses):
        self.iface = iface
        self.addresses = []
        for address in addresses:
            self.addresses.append(ip_interface(address))

    def apply(self, ignore, ign_dynamic, do_apply):
        logger.debug('getting addresses', extra={'iface': self.iface})

        # get ifindex
        idx = next(iter(ipr.link_lookup(ifname=self.iface)), None)

        if idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get active ip addresses
        ipr_addr = {}
        addr_add = []
        for addr in ipr.get_addr(index=idx):
            ip = ip_interface(addr.get_attr('IFA_ADDRESS') + '/' + str(addr['prefixlen']))
            ipr_addr[ip] = addr

        for addr in self.addresses:
            if addr in ipr_addr:
                logger.info(' %s', addr.with_prefixlen, extra={'iface': self.iface, 'style': IfStateLogging.STYLE_OK})
                del ipr_addr[addr]
            else:
                addr_add.append(addr)

        for ip, addr in ipr_addr.items():
            if not any(ip in net for net in ignore):
                if not ign_dynamic or ipr_addr[ip]['flags'] & IFA_F_PERMANENT == IFA_F_PERMANENT:
                    logger.info('-%s', ip.with_prefixlen, extra={'iface': self.iface, 'style': IfStateLogging.STYLE_DEL})
                    if do_apply:
                        ipr.addr("del", index=idx, address=str(ip.ip), mask=ip.network.prefixlen)

        for addr in addr_add:
            logger.info('+%s', addr.with_prefixlen, extra={'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
            if do_apply:
                ipr.addr("add", index=idx, address=str(addr.ip), mask=addr.network.prefixlen)
