from libifstate.log import logger, IfStateLogging
from pyroute2 import IPRoute

from pyroute2.netlink.rtnl.tcmsg import tcmsg
from pyroute2.netlink.rtnl import RTM_DELTFILTER
from pyroute2.netlink import NLM_F_REQUEST
from pyroute2.netlink import NLM_F_ACK
from pyroute2.netlink import NLM_F_CREATE
from pyroute2.netlink import NLM_F_EXCL


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


ipr = IPRouteExt()
