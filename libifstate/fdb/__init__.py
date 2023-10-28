from libifstate.util import logger, IfStateLogging
from libifstate.exception import netlinkerror_classes
from ipaddress import ip_address
from pyroute2.netlink.rtnl.ndmsg import NUD_NOARP, NUD_PERMANENT, NTF_SELF
from pyroute2.config import AF_BRIDGE

class FDB():
    def __init__(self, netns, iface, fdb):
        self.netns = netns
        self.iface = iface
        self.fdb = {}
        self.state_mask = NUD_NOARP|NUD_PERMANENT
        for entry in fdb:
            lladdr = entry['lladdr'].lower()
            _entry = {
                'lladdr': lladdr,
            }

            if 'port' not in entry:
                _entry['port'] = 8472
            else:
                _entry['port'] = entry['port']

            if 'dst' in entry:
                _entry['dst'] = str(ip_address(entry['dst']))

            if 'state' in entry:
                _entry['state'] = 0
                for name, value in pyroute2.netlink.rtnl.ndmsg.states.items():
                    if name in entry['state']:
                        _entry['state'] |= value
            else:
                _entry['state'] = NUD_NOARP|NUD_PERMANENT

            if 'flags' in entry:
                _entry['flags'] = 0
                for name, value in pyroute2.netlink.rtnl.ndmsg.flags.items():
                    if name in entry['flags']:
                        _entry['flags'] |= value
            else:
                _entry['flags'] = NTF_SELF

            if not lladdr in self.fdb:
                self.fdb[lladdr] = [_entry]
            else:
                self.fdb[lladdr].append(_entry)

    def apply(self, do_apply):
        logger.debug('getting fdb', extra={'iface': self.iface})

        # get ifindex
        idx = next(iter(self.netns.ipr.link_lookup(ifname=self.iface)), None)

        if idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get fdb entries (NUD_NOARP|NUD_PERMANENT)
        ipr_entries = {}
        for entry in self.netns.ipr.get_neighbours(ifindex=idx, family=AF_BRIDGE):
            state = entry.get('state')

            # look for permanent (local) or noarp (static) entries, only
            if not state & self.state_mask:
                continue

            lladdr = entry.get_attr('NDA_LLADDR')
            _entry = {
                'lladdr': lladdr,
                'state': state,
                'flags': entry.get('flags')
            }

            attr = entry.get_attr('NDA_DST')
            if attr is not None:
                _entry['dst'] = str(ip_address(attr))

            attr = entry.get_attr('NDA_PORT')
            if attr is None or attr == 0:
                _entry['port'] = 8472
            else:
                _entry['port'] = attr

            if not lladdr in ipr_entries:
                ipr_entries[lladdr] = [_entry]
            else:
                ipr_entries[lladdr].append(_entry)

        # configure fdb entries unconditionally
        for lladdr, entries in self.fdb.items():
            for entry in entries:
                # check if fdb entry is already present
                if lladdr in ipr_entries:
                    if entry in ipr_entries[lladdr]:
                        logger.log_ok('fdb', '= {}'.format(lladdr))
                        continue

                # fdb entry needs to be added
                logger.log_add('fdb', '+ {}'.format(lladdr))

                # prepare arguments
                args = {
                    'ifindex': idx,
                    'family': AF_BRIDGE
                }
                args.update(entry)
                logger.debug("bridge fdb append: {}".format(
                    " ".join("{}={}".format(k, v) for k, v in args.items())))

                if do_apply:
                    try:
                        self.netns.ipr.fdb("append", **args)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('add {} to fdb failed: {}'.format(
                            entry['lladdr'], err.args[1]))

        # for ip, lladdr in ipr_neigh.items():
        #     logger.log_del('neighbours', '- {}'.format(str(ip)))
        #     try:
        #         if do_apply:
        #             self.netns.ipr.neigh("del", ifindex=idx, dst=str(
        #                 ip))
        #     except Exception as err:
        #         if not isinstance(err, netlinkerror_classes):
        #             raise
        #         logger.warning('removing neighbour {} failed: {}'.format(
        #             str(ip), err.args[1]))

        # for ip, lladdr in neigh_add.items():
        #     logger.log_add('neighbours', '+ {}'.format(str(ip)))
        #     if do_apply:
        #         try:
        #             opts = {
        #                 'ifindex': idx,
        #                 'dst': str(ip),
        #                 'lladdr': lladdr,
        #                 'state': 128
        #             }

        #             self.netns.ipr.neigh('replace', **opts)
        #         except Exception as err:
        #             if not isinstance(err, netlinkerror_classes):
        #                 raise
        #             logger.warning('adding neighbour {} failed: {}'.format(
        #                 str(ip), err.args[1]))
