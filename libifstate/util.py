from libifstate.log import logger, IfStateLogging
from pyroute2 import IPRoute, NetNS, netns

from pyroute2.netlink.rtnl.tcmsg import tcmsg
from pyroute2.netlink.rtnl import RTM_DELTFILTER, RTM_NEWNSID
from pyroute2.netlink.rtnl.nsidmsg import nsidmsg
from pyroute2.netlink import NLM_F_REQUEST
from pyroute2.netlink import NLM_F_ACK
from pyroute2.netlink import NLM_F_CREATE
from pyroute2.netlink import NLM_F_EXCL

try:
    # pyroute2 <0.6
    from pyroute2.ethtool.ioctl import SIOCETHTOOL
except ModuleNotFoundError:
    # pyroute2 >= 0.6
    from pr2modules.ethtool.ioctl import SIOCETHTOOL

import socket
import fcntl
import struct
import array
import struct
import typing

# ethtool helper
ETHTOOL_GDRVINFO = 0x00000003  # Get driver info
STRUCT_DRVINFO = struct.Struct(
    "I" +    # cmd
    "32s" +  # driver
    "32s" +  # version
    "32s" +  # fw_version
    "32s" +  # bus_info
    "32s" +  # reserved1
    "12s" +  # reserved2
    "I" +    # n_priv_flags
    "I" +    # n_stats
    "I" +    # testinfo_len
    "I" +    # eedump_len
    "I"      # regdump_len
)

ETHTOOL_GPERMADDR = 0x00000020  # Get permanent hardware address
L2_ADDRLENGTH = 6  # L2 address length

root_ipr = typing.NewType("IPRouteExt", IPRoute)

def filter_ifla_dump(showall, ifla, defaults, prefix="IFLA"):
    dump = {}

    for key, default_value in defaults.items():
        current_value = next(iter(ifla.get_attrs("_".join((prefix, key.upper())))), None)

        if current_value is not None:
            if showall or default_value is None or default_value != current_value:
                dump[key] = current_value

    return dump

class IPRouteExt(IPRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def del_filter_by_info(self, index=0, handle=0, info=0, parent=0):
        msg = tcmsg()
        msg['index'] = index
        msg['handle'] = handle
        msg['info'] = info
        if parent != 0:
            msg['parent'] = parent

        return tuple(self.nlm_request(
            msg,
            msg_type=RTM_DELTFILTER,
            msg_flags=NLM_F_REQUEST |
            NLM_F_ACK
        ))

    def get_businfo(self, ifname):
        data = array.array("B", struct.pack(
            "I", ETHTOOL_GDRVINFO))
        data.extend(b'\x00' * (STRUCT_DRVINFO.size - len(data)))

        ifr = struct.pack('16sP', ifname.encode(
            "utf-8"), data.buffer_info()[0])

        try:
            r = fcntl.ioctl(self.__sock.fileno(), SIOCETHTOOL, ifr)
        except OSError:
            return None

        drvinfo = STRUCT_DRVINFO.unpack(data)

        return drvinfo[4].decode('ascii').split('\x00')[0]

    def get_permaddr(self, ifname):
        data = array.array("B", struct.pack(
            "II", ETHTOOL_GPERMADDR, L2_ADDRLENGTH))
        data.extend(b'\x00' * L2_ADDRLENGTH)

        ifr = struct.pack('16sP', ifname.encode(
            "utf-8"), data.buffer_info()[0])

        try:
            r = fcntl.ioctl(self.__sock.fileno(), SIOCETHTOOL, ifr)
        except OSError:
            return None

        l2addr = ":".join(format(x, "02x") for x in data[8:])
        if l2addr == "00:00:00:00:00:00":
            return None

        return l2addr

    def get_iface_by_businfo(self, businfo):
        for iface in iter(self.get_links()):
            ifname = iface.get_attr('IFLA_IFNAME')
            bi = self.get_businfo(ifname)

            if bi and bi == businfo:
                return iface['index']

    def get_iface_by_permaddr(self, permaddr):
        for iface in iter(self.get_links()):
            ifname = iface.get_attr('IFLA_IFNAME')
            addr = self.get_permaddr(ifname)

            if addr and addr == permaddr:
                return iface['index']

        return None

    def get_ifname_by_index(self, index):
        link = next(iter(self.get_links(index)), None)

        if link is None:
            return index

        return link.get_attr('IFLA_IFNAME')

    def set_netnsid(self, nsid=None, pid=None, fd=None):
        '''
        call pyroute2's set_netnsid if available or use
        fallback implementation for pyroute2 <=0.79
        '''
        if hasattr(super(), 'set_netnsid'):
            return super().set_netnsid(nsid, pid, fd)
        else:
            msg = nsidmsg()

            if nsid is None or nsid < 0:
                # kernel auto select
                msg['attrs'].append(('NETNSA_NSID', 4294967295))
            else:
                msg['attrs'].append(('NETNSA_NSID', nsid))

            if pid is not None:
                msg['attrs'].append(('NETNSA_PID', pid))

            if fd is not None:
                msg['attrs'].append(('NETNSA_FD', fd))

            return self.nlm_request(msg, RTM_NEWNSID, NLM_F_REQUEST | NLM_F_ACK)

class NetNSExt(NetNS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            netns.pushns(self.netns)
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        finally:
            netns.popns()

    def del_filter_by_info(self, index=0, handle=0, info=0, parent=0):
        msg = tcmsg()
        msg['index'] = index
        msg['handle'] = handle
        msg['info'] = info
        if parent != 0:
            msg['parent'] = parent

        return tuple(self.nlm_request(
            msg,
            msg_type=RTM_DELTFILTER,
            msg_flags=NLM_F_REQUEST |
            NLM_F_ACK
        ))

    def get_businfo(self, ifname):
        data = array.array("B", struct.pack(
            "I", ETHTOOL_GDRVINFO))
        data.extend(b'\x00' * (STRUCT_DRVINFO.size - len(data)))

        ifr = struct.pack('16sP', ifname.encode(
            "utf-8"), data.buffer_info()[0])

        try:
            r = fcntl.ioctl(self.__sock.fileno(), SIOCETHTOOL, ifr)
        except OSError:
            return None

        drvinfo = STRUCT_DRVINFO.unpack(data)

        return drvinfo[4].decode('ascii').split('\x00')[0]

    def get_permaddr(self, ifname):
        data = array.array("B", struct.pack(
            "II", ETHTOOL_GPERMADDR, L2_ADDRLENGTH))
        data.extend(b'\x00' * L2_ADDRLENGTH)

        ifr = struct.pack('16sP', ifname.encode(
            "utf-8"), data.buffer_info()[0])

        try:
            r = fcntl.ioctl(self.__sock.fileno(), SIOCETHTOOL, ifr)
        except OSError:
            return None

        l2addr = ":".join(format(x, "02x") for x in data[8:])
        if l2addr == "00:00:00:00:00:00":
            return None

        return l2addr

    def get_iface_by_businfo(self, businfo):
        for iface in iter(self.get_links()):
            ifname = iface.get_attr('IFLA_IFNAME')
            bi = self.get_businfo(ifname)

            if bi and bi == businfo:
                return iface['index']

    def get_iface_by_permaddr(self, permaddr):
        for iface in iter(self.get_links()):
            ifname = iface.get_attr('IFLA_IFNAME')
            addr = self.get_permaddr(ifname)

            if addr and addr == permaddr:
                return iface['index']

        return None

    def get_ifname_by_index(self, index):
        link = next(iter(self.get_links(index)), None)

        if link is None:
            return index

        return link.get_attr('IFLA_IFNAME')

    def set_netnsid(self, nsid=None, pid=None, fd=None):
        '''
        call pyroute2's set_netnsid if available or use
        fallback implementation for pyroute2 <=0.79
        '''
        if hasattr(super(), 'set_netnsid'):
            return super().set_netnsid(nsid, pid, fd)
        else:
            msg = nsidmsg()

            if nsid is None or nsid < 0:
                # kernel auto select
                msg['attrs'].append(('NETNSA_NSID', 4294967295))
            else:
                msg['attrs'].append(('NETNSA_NSID', nsid))

            if pid is not None:
                msg['attrs'].append(('NETNSA_PID', pid))

            if fd is not None:
                msg['attrs'].append(('NETNSA_FD', fd))

            return self.nlm_request(msg, RTM_NEWNSID, NLM_F_REQUEST | NLM_F_ACK)

class LinkDependency:
    def __init__(self, ifname, netns):
        self.ifname = ifname
        self.netns = netns

    def __hash__(self):
        return hash((self.ifname, self.netns))

    def __eq__(self, other):
        return (self.ifname, self.netns) == (other.ifname, other.netns)

    def __lt__(self, obj):
        if self.netns is None:
            if obj.netns is not None:
                return True
        elif obj.netns is None:
            return False

        if self.netns != obj.netns:
            return self.netns < obj.netns

        if self.ifname == obj.ifname:
            return False

        if self.ifname == 'lo':
            return True

        if obj.ifname == 'lo':
            return False

        return self.ifname < obj.ifname

    def __ne__(self, other):
        return not(self == other)

    def __str__(self):
        if self.netns is None:
            return "{}".format(self.ifname)
        else:
            return "{}[netns={}]".format(self.ifname, self.netns)


root_ipr = IPRouteExt()
