from libifstate.util import logger, ipr
from ipaddress import ip_interface

class Addresses():
    def __init__(self, iface, addresses):
        self.iface = iface
        self.addresses = []
        for address in addresses:
            self.addresses.append(ip_interface(address))

    def commit(self):
        logger.debug('getting addresses', extra={'iface': self.iface})
        #ipr_addr = ipr.get_addr( ipr.get_link() )
        print("{} => {}".format(self.iface, self.addresses))
