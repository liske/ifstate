from libifstate.util import logger, ipr, LogStyle
from ipaddress import ip_interface
#from pyroute2.netlink.rtnl.ifaddrmsg import ifaddrmsg

class Addresses():
    def __init__(self, iface, addresses):
        self.iface = iface
        self.addresses = []
        for address in addresses:
            self.addresses.append(ip_interface(address))

    def apply(self, ignore):
        logger.debug('getting addresses', extra={'iface': self.iface})

        # get ifindex
        idx = next(iter(ipr.link_lookup(ifname=self.iface)))

        # get active ip addresses
        ipr_addr = {}
        for addr in ipr.get_addr(index=idx):
            ip = ip_interface(addr.get_attr('IFA_ADDRESS') + '/' + str(addr['prefixlen']))
            ipr_addr[ip] = addr
#            ipr_flags[ip] = ifaddrmsg.flags2names(addr['flags'], family=addr['family'])

        for addr in self.addresses:
            ip = str(addr.ip)
            if addr in ipr_addr:
                logger.info('%s', addr.with_prefixlen, extra={'iface': self.iface, 'style': LogStyle.OK})
                del ipr_addr[addr]
            else:
                logger.info('%s', addr.with_prefixlen, extra={'iface': self.iface, 'style': LogStyle.CHG})
                ipr.addr("add", index=idx, address=ip, mask=addr.network.prefixlen)

        for ip, addr in ipr_addr.items():
            if not any(ip in net for net in ignore):
#                if 'IFA_F_PERMANENT' in ipr_flags[ip]:
                logger.info('%s', ip.with_prefixlen, extra={'iface': self.iface, 'style': LogStyle.DEL})
                ipr.addr("del", index=idx, address=str(ip.ip), mask=ip.network.prefixlen)
