#!/usr/bin/env python3

from pyroute2 import IPRoute
from pyroute2.netlink.exceptions import NetlinkError

ipr = IPRoute()

try:
    link = next(iter(ipr.get_links(666)), None)
except NetlinkError as err:
    print('lookup failed: {}'.format(err.args[1]))
