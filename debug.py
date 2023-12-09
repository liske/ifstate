#!/usr/bin/env python3

import readline # optional, will allow Up/Down/History in the console
import code

from pyroute2 import IPRoute
from pprint import pprint

ipr = IPRoute()

print("""Symbols:
  ipr: pyroute2.IPRoute() object
  pprint: Data pretty printer function
""")


print("Interfaces:")
for link in ipr.get_links():
    print("  {:2}: {}".format(link.get('index'),link.get_attr( 'IFLA_IFNAME')))

print("")

variables = globals().copy()
variables.update(locals())
shell = code.InteractiveConsole(variables)
shell.interact()