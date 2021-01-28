from libifstate.util import logger, IfStateLogging
from libifstate.exception import NetlinkError
from wgnlpy import WireGuard as WG
from ipaddress import ip_network
import collections

wg = WG()


class WireGuard():
    def __init__(self, iface, wireguard):
        self.iface = iface
        self.wireguard = wireguard

        # convert allowedips peers settings into IPv[46]Network objects
        # and remove duplicates
        if 'peers' in self.wireguard:
            for i, peer in enumerate(self.wireguard['peers']):
                if 'allowedips' in peer:
                    self.wireguard['peers'][i]['allowedips'] = set(
                        [ip_network(x) for x in self.wireguard['peers'][i]['allowedips']])

    def apply(self, do_apply):
        # get kernel's wireguard settings for the interface
        try:
            state = wg.get_interface(
                self.iface, spill_private_key=True, spill_preshared_keys=True)
        except Exception as err:
            logger.warning('WireGuard on {} failed: {}'.format(
                self.iface, err.args[1]))
            return

        # check base settings (not the peers, yet)
        has_changes = False
        for setting in [x for x in self.wireguard.keys() if x != 'peers']:
            logger.debug('  %s: %s => %s', setting, getattr(
                state, setting), self.wireguard[setting], extra={'iface': self.iface})
            has_changes |= self.wireguard[setting] != getattr(state, setting)

        if has_changes:
            logger.info('change [iface]', extra={
                        'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
            if do_apply:
                try:
                    wg.set_interface(
                        self.iface, **{k: v for k, v in self.wireguard.items() if k != "peers"})
                except NetlinkError as err:
                    logger.warning('updating iface {} failed: {}'.format(
                        self.iface, err.args[1]))
        else:
            logger.info('ok [iface]', extra={
                        'iface': self.iface, 'style': IfStateLogging.STYLE_OK})

        # check peers list if provided
        if 'peers' in self.wireguard:
            peers = getattr(state, 'peers')
            has_pchanges = False

            avail = []
            for peer in self.wireguard['peers']:
                avail.append(peer['public_key'])
                pubkey = next(
                    iter([x for x in peers.keys() if x == peer['public_key']]), None)
                if pubkey is None:
                    has_pchanges = True
                    if do_apply:
                        try:
                            wg.set_peer(self.iface, **peer)
                        except NetlinkError as err:
                            logger.warning('add peer to {} failed: {}'.format(
                                self.iface, err.args[1]))
                else:
                    pchange = False
                    for setting in peer.keys():
                        attr = getattr(peers[pubkey], setting)
                        logger.debug('  peer.%s: %s => %s', setting, attr,
                                     peer[setting], extra={'iface': self.iface})
                        if type(attr) == list:
                            pchange |= collections.Counter(
                                attr) != collections.Counter(peer[setting])
                        else:
                            pchange |= str(peer[setting]) != str(getattr(
                                peers[pubkey], setting))

                    if pchange:
                        has_pchanges = True
                        if do_apply:
                            try:
                                wg.set_peer(self.iface, **peer)
                            except NetlinkError as err:
                                logger.warning('change peer at {} failed: {}'.format(
                                    self.iface, err.args[1]))

            for peer in peers:
                if not peer in avail:
                    has_pchanges = True
                    if do_apply:
                        try:
                            wg.remove_peers(self.iface, peer)
                        except NetlinkError as err:
                            logger.warning('remove peer from {} failed: {}'.format(
                                self.iface, err.args[1]))
            if has_pchanges:
                logger.info('change [peers]', extra={
                            'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
            else:
                logger.info('ok [peers]', extra={
                            'iface': self.iface, 'style': IfStateLogging.STYLE_OK})
