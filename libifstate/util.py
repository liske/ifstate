from libifstate.log import logger, IfStateLogging
from pyroute2 import IPRoute

from pyroute2.netlink.rtnl.tcmsg import tcmsg
from pyroute2.netlink.rtnl import RTM_DELTFILTER
from pyroute2.netlink import NLM_F_REQUEST
from pyroute2.netlink import NLM_F_ACK
from pyroute2.netlink import NLM_F_CREATE
from pyroute2.netlink import NLM_F_EXCL
from pyroute2.ethtool.ioctl import SIOCETHTOOL

import socket
import fcntl
import struct
import array
import struct

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
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class IPRouteExt(IPRoute):
    def del_filter_by_info(self, index=0, handle=0, info=0, parent=0):
        msg = tcmsg()
        msg['index'] = index
        msg['handle'] = handle
        msg['info'] = info
        if parent != 0:
            msg['parent'] = parent

        return tuple(ipr.nlm_request(
            msg,
            msg_type=RTM_DELTFILTER,
            msg_flags=NLM_F_REQUEST |
            NLM_F_ACK | NLM_F_CREATE | NLM_F_EXCL
        ))

    def get_businfo(self, ifname):
        data = array.array("B", struct.pack(
            "I", ETHTOOL_GDRVINFO))
        data.extend(b'\x00' * (STRUCT_DRVINFO.size - len(data)))

        ifr = struct.pack('16sP', ifname.encode(
            "utf-8"), data.buffer_info()[0])

        try:
            r = fcntl.ioctl(sock.fileno(), SIOCETHTOOL, ifr)
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
            r = fcntl.ioctl(sock.fileno(), SIOCETHTOOL, ifr)
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
        link = next(iter(ipr.get_links(index)), None)

        if link is None:
            return index

        return link.get_attr('IFLA_IFNAME')


ipr = IPRouteExt()
