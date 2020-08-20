from libifstate.util import logger, IfStateLogging

import os


class Sysctl():
    def __init__(self):
        self.sysctls = {}

    def add(self, iface, sysctl):
        self.sysctls[iface] = sysctl

    def set_sysctl(self, iface, family, key, val, do_apply):
        fn = '/proc/sys/net/{}/conf/{}/{}'.format(family, iface, key)
        with open(fn) as fh:
            current = fh.readline().rstrip()
        if current == str(val):
            logger.info(
                'ok', extra={'iface': "{}/{}".format(family, key), 'style': IfStateLogging.STYLE_OK})
        else:
            logger.info(
                'set', extra={'iface': "{}/{}".format(family, key), 'style': IfStateLogging.STYLE_CHG})
            if do_apply:
                try:
                    with open(fn, 'w') as fh:
                        fh.writelines([str(val)])
                except OSError as err:
                    logger.warning('updating sysctl {}/{} failed: {}'.format(
                        family, key, err.args[1]))

    def apply(self, iface, do_apply):
        if not iface in self.sysctls:
            logger.debug("no sysctl settings", extra={'iface': iface})
            return

        for family in self.sysctls[iface].keys():
            for key, val in self.sysctls[iface][family].items():
                self.set_sysctl(iface, family, key, val, do_apply)

    def has_settings(self, iface):
        return iface in self.sysctls
