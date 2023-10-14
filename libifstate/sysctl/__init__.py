from libifstate.util import logger, IfStateLogging
import pyroute2.netns

import os


class Sysctl():
    def __init__(self, netns):
        self.sysctls = {}
        self.globals = {}
        self.netns = netns

    def add(self, iface, sysctl):
        self.sysctls[iface] = sysctl

    def add_global(self, proto, sysctl):
        self.globals[proto] = sysctl

    def set_sysctl(self, iface_current, iface_config, family, key, val, do_apply):
        if self.netns.netns is not None:
            pyroute2.netns.pushns(self.netns.netns)

        log_str = "{}/{}".format(family, key)
        if self.netns.netns is not None:
            log_str += "[netns={}]".format(self.netns.netns)

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
                logger.log_ok(log_str)
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
                logger.log_change(log_str)
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

    def apply_globals(self, do_apply):
        changes = []
        for proto, sysctl in self.globals.items():
            for key, val in sysctl.items():
                if self.set_sysctl('..', '..', proto, key, val, do_apply):
                    changes.append(proto)
        return changes

    def has_globals(self):
        return len(self.globals) > 0
