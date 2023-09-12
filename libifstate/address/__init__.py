from libifstate.util import logger, IfStateLogging
from libifstate.exception import netlinkerror_classes
from ipaddress import ip_interface
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_PERMANENT


class Addresses():
    def __init__(self, netns, iface, addresses):
        self.netns = netns
        self.iface = iface
        self.addresses = []
        for address in addresses:
            self.addresses.append(ip_interface(address))

    def apply(self, ignore, ign_dynamic, do_apply):
        logger.debug('getting addresses', extra={'iface': self.iface, 'netns': self.netns})

        # get ifindex
        idx = next(iter(self.netns.ipr.link_lookup(ifname=self.iface)), None)

        if idx == None:
            logger.warning('link missing', extra={'iface': self.iface, 'netns': self.netns})
            return

        # get active ip addresses
        ipr_addr = {}
        addr_add = []
        for addr in self.netns.ipr.get_addr(index=idx):
            ip = ip_interface(addr.get_attr('IFA_ADDRESS') +
                              '/' + str(addr['prefixlen']))
            ipr_addr[ip] = addr

        for addr in self.addresses:
            if addr in ipr_addr:
                logger.log_ok('addresses', '= {}'.format(addr.with_prefixlen))
                del ipr_addr[addr]
            else:
                addr_add.append(addr)

        for ip, addr in ipr_addr.items():
            if not any(ip in net for net in ignore):
                if not ign_dynamic or ipr_addr[ip]['flags'] & IFA_F_PERMANENT == IFA_F_PERMANENT:
                    logger.log_del('addresses', '- {}'.format(ip.with_prefixlen))
                    try:
                        if do_apply:
                            self.netns.ipr.addr("del", index=idx, address=str(
                                ip.ip), mask=ip.network.prefixlen)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('removing ip {}/{} failed: {}'.format(
                            str(ip.ip), ip.network.prefixlen, err.args[1]))

        for addr in addr_add:
            logger.log_change('addresses', '+ {}'.format(addr.with_prefixlen))
            if do_apply:
                try:
                    self.netns.ipr.addr("add", index=idx, address=str(
                        addr.ip), mask=addr.network.prefixlen)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('adding ip {}/{} failed: {}'.format(
                        str(addr.ip), addr.network.prefixlen, err.args[1]))
