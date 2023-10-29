from libifstate.util import logger, IfStateLogging
from libifstate.exception import netlinkerror_classes
from ipaddress import ip_address
from pyroute2.netlink.rtnl.ndmsg import NUD_NOARP, NUD_PERMANENT, NTF_SELF
from pyroute2.config import AF_BRIDGE
import pyroute2.netlink.rtnl.ndmsg

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

            if 'flags' in entry:
                _entry['flags'] = 0
                for name, value in pyroute2.netlink.rtnl.ndmsg.flags.items():
                    if name in entry['flags']:
                        _entry['flags'] |= value
            else:
                _entry['flags'] = NTF_SELF

            for opt in ['nhid', 'src_vni', 'vni']:
                if opt in entry:
                    _entry[opt] = entry[opt]

            if not lladdr in self.fdb:
                self.fdb[lladdr] = [_entry]
            else:
                self.fdb[lladdr].append(_entry)

    def get_kernel_fdb(self):
        # get fdb entries (NUD_NOARP|NUD_PERMANENT)
        fdb = {}
        for entry in self.netns.ipr.get_neighbours(ifindex=self.idx, family=AF_BRIDGE):
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

            for opt in ['nhid', 'src_vni', 'vni']:
                attr = entry.get_attr(f"NDA_{opt.upper()}")
                if attr is not None:
                    _entry[opt] = attr

            if not lladdr in fdb:
                fdb[lladdr] = [_entry]
            else:
                fdb[lladdr].append(_entry)

        return fdb

    def apply(self, do_apply):
        logger.debug('getting fdb', extra={'iface': self.iface})

        # get ifindex and lladdr
        link = next(iter(self.netns.ipr.get_links(ifname=self.iface)), None)

        if link == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        self.idx = link['index']
        self.lladdr = link.get_attr('IFLA_ADDRESS')

        # prepare default state for entries w/o state specified (depends on link type)
        default_state = NUD_PERMANENT

        linkinfo = link.get_attr('IFLA_LINKINFO')
        if linkinfo and linkinfo.get_attr('IFLA_INFO_KIND') in ['vxlan']:
            default_state |= NUD_NOARP

        # configure fdb entries
        ipr_entries = self.get_kernel_fdb()
        for lladdr, entries in self.fdb.items():
            for entry in entries:
                # set default_state if missing
                if not 'state' in entry:
                    entry['state'] = default_state

                # check if fdb entry is already present
                if lladdr in ipr_entries:
                    if entry in ipr_entries[lladdr]:
                        logger.log_ok('fdb', '= {}'.format(lladdr))
                        continue

                # fdb entry needs to be added
                logger.log_add('fdb', '+ {}'.format(lladdr))

                # prepare arguments
                args = {
                    'ifindex': self.idx,
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

        # cleanup orphan fdb entries
        ipr_entries = self.get_kernel_fdb()
        for lladdr, entries in ipr_entries.items():
            # ignore lladdr of the link
            if lladdr == self.lladdr:
                continue

            for entry in entries:
                # check if fdb entry is already present
                if lladdr not in self.fdb or entry not in self.fdb[lladdr]:
                    logger.log_del('fdb', '- {}'.format(lladdr))

                    # prepare arguments
                    args = {
                        'ifindex': self.idx,
                        'family': AF_BRIDGE
                    }
                    args.update(entry)
                    logger.debug("bridge fdb del: {}".format(
                        " ".join("{}={}".format(k, v) for k, v in args.items())))

                    if do_apply:
                        try:
                            self.netns.ipr.fdb("del", **args)
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            logger.warning('remove {} from fdb failed: {}'.format(
                                entry['lladdr'], err.args[1]))
