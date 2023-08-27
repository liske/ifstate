from libifstate.util import logger, IfStateLogging
import pyroute2.netns

import os


class Sysctl():
    def __init__(self, netns):
        self.sysctls = {}
        self.netns = netns

    def add(self, iface, sysctl):
        self.sysctls[iface] = sysctl

    def set_sysctl(self, iface_current, iface_config, family, key, val, do_apply):
        if self.netns.netns is not None:
            pyroute2.netns.pushns(self.netns.netns)

        try:
            fn = '/proc/sys/net/{}/conf/{}/{}'.format(family, iface_current, key)
            try:
                with open(fn) as fh:
                    current = fh.readline().rstrip()
            except OSError as err:
                logger.warning('reading sysctl {}/{} failed: {}'.format(
                    family, key, err.args[1]))
                return
            if current == str(val):
                logger.debug('  %s/%s: %s == %s', family, key, current, val, extra={'iface': iface_config, 'netns': self.netns})
                logger.info(
                    'ok (%s/%s)', family, key, extra={'iface': iface_config, 'netns': self.netns, 'style': IfStateLogging.STYLE_OK})
                return False
            else:
                logger.debug('  %s/%s: %s => %s', family, key, current, val, extra={'iface': iface_config, 'netns': self.netns})
                if do_apply:
                    try:
                        with open(fn, 'w') as fh:
                            fh.writelines([str(val)])
                    except OSError as err:
                        logger.warning('updating sysctl {}/{} failed: {}'.format(
                            family, key, err.args[1]))
                logger.info(
                    'change (%s/%s)', family, key, extra={'iface': iface_config, 'netns': self.netns, 'style': IfStateLogging.STYLE_CHG})
                return True
        finally:
            if self.netns.netns is not None:
                pyroute2.netns.popns()

    def apply(self, iface_current, do_apply, iface_config=None):
        # if None the interface has already the final name..
        if iface_config is None:
            iface_config = iface_current

        if not iface_config in self.sysctls:
            logger.debug("no sysctl settings", extra={'iface': iface_config})
            return

        logger.debug('checking sysctl', extra={'iface': iface_config})

        changes = False
        for family in self.sysctls[iface_config].keys():
            for key, val in self.sysctls[iface_config][family].items():
                changes = changes or self.set_sysctl(iface_current, iface_config, family, key, val, do_apply)

    def has_settings(self, iface):
        return iface in self.sysctls
