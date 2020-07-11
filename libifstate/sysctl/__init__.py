from libifstate.util import logger, LogStyle

import os


class Sysctl():
    def __init__(self):
        self.sysctls = {}

    def add(self, iface, sysctl):
        self.sysctls[iface] = sysctl

    def set_sysctl(self, iface, family, key, val, do_apply):
        with open('/proc/sys/net/{}/conf/{}/{}'.format(family, iface, key)) as fh:
            current = fh.readline().rstrip()
        if current == str(val):
            logger.info(
                'ok', extra={'iface': "{}/{}".format(family, key), 'style': LogStyle.OK})
        else:
            logger.info(
                'set', extra={'iface': "{}/{}".format(family, key), 'style': LogStyle.CHG})

    def apply(self, iface, do_apply):
        if not iface in self.sysctls:
            logger.debug("no sysctl settings", extra={'iface': iface})
            return

        for family in self.sysctls[iface].keys():
            for key, val in self.sysctls[iface][family].items():
                self.set_sysctl(iface, family, key, val, do_apply)

    def has_settings(self, iface):
        return iface in self.sysctls
