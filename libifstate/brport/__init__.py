from libifstate.util import logger, ipr, IfStateLogging, filter_ifla_dump
from libifstate.exception import netlinkerror_classes


class BRPort():
    ILFA_DEFAULTS = {
        "priority": 32,
        "guard": 0,
        "mode": 0,
        "fast_leave": 0,
        "protect": 0,
        "learning": 1,
        "unicast_flood": 1,
        "bcast_flood": 1,
        "mcast_flood": 1,
        "mcast_to_ucast": 0,
        "proxyarp": 0,
        "proxyarp_wifi": 0,
        "neigh_suppress": 0,
        "vlan_tunnel": 0,
        "backup_port": None,
        "isolated": 0,
    }

    def __init__(self, iface, brport):
        self.iface = iface
        self.brport = brport

    def depends(self):
        '''get link dependencies (i.e. backup port)'''

        backup_port = self.brport.get('backup_port')

        if backup_port:
            return (backup_port,)
        else:
            return ()

    def has_changes(self, idx):
        logger.debug('checking brport', extra={'iface': self.iface})

        has_changes = False
        brport_state = next(iter(ipr.brport('dump', index=idx)), None)

        # no a bridge port
        if brport_state is None:
            logger.debug('  not a bridge port', extra={'iface': self.iface})
            return True

        for setting in self.brport.keys():

            current_value = next(iter(next(iter(brport_state.get_attrs(
                'IFLA_PROTINFO'))).get_attrs('IFLA_BRPORT_{}'.format(setting.upper()))))

            logger.debug('  %s: %s => %s', setting, current_value, self.brport[setting], extra={
                         'iface': self.iface})
            has_changes |= current_value != self.brport[setting]

        return has_changes

    def apply(self, do_apply, idx, excpts):
        brport_state = ipr.brport('dump', index=idx)
        if brport_state == None:
            logger.warning('link is not a bridge port',
                           extra={'iface': self.iface})
            return

        logger.info(
            'change (brport)', extra={'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})

        logger.debug("bridge link set: {}".format(
            " ".join("{}={}".format(k, v) for k, v in self.brport.items())))

        if do_apply:
            try:
                ipr.brport('set', index=idx, **(self.brport))
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                excpts.add('brport', err, **(self.brport))

    def show(showall, idx, config):
        brport_state = next(iter(ipr.brport('dump', index=idx)), None)

        if not brport_state:
            return

        proinfo = next(iter(brport_state.get_attrs('IFLA_PROTINFO')))

        dump = filter_ifla_dump(showall, proinfo, BRPort.ILFA_DEFAULTS, "IFLA_BRPORT")
        if dump:
            config['brport'] = dump
