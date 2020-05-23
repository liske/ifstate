#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.util import logger
from collections import namedtuple

import argparse
import logging
import yaml

class Actions():
    CHECK = "check"
    CONFIGURE = "configure"
    DESCRIBE = "describe"

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet", action="store_true", help="be more quiet, print only warnings and errors")
    group.add_argument("-v", "--verbose", action="store_true", help="be more verbose")
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-c", "--config", type=str, default="/etc/ifstate/config.yml", help="configuration YaML filename")
    parser.add_argument("action", choices=list(a.lower() for a in dir(Actions) if not a.startswith('_')), help="specifies the action to perform")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif args.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    ifs = IfState()

    if args.action == Actions.DESCRIBE:
        print(yaml.dump(ifs.describe()))

    if args.action in [Actions.CHECK, Actions.CONFIGURE]:
        parser = YamlParser(args.config)
        ifstates = parser.config()

        ifs.update(ifstates)

        if args.action == Actions.CHECK:
            pass
        else:
            ifs.commit()

if __name__ == "__main__":
    main()
