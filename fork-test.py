#!/usr/bin/env python3

from pyroute2 import IPRoute
import os
import time

ipr = IPRoute()
processes = 2

child_pid = os.fork()

if child_pid == 0 and processes & 1 == 1:
    while True:
        links = ipr.get_links(index=1)
        print(f"CHILD : {links[0].get_attr('IFLA_IFNAME')}")
        time.sleep(0.1)
else:
    if processes & 2 == 2:
        while True:
            links = ipr.get_links(index=2)
            print(f"PARENT: {links[0].get_attr('IFLA_IFNAME')}")
            time.sleep(0.1)

    os.waitpid(child_pid, 0)
