#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import IfState
from libifstate.util import logger
from collections import namedtuple

import argparse
import logging
import yaml

class Actions():
    CHECK = "check"
    CONFIG = "config"
    TEMPLATE = "template"

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug", action="store_true")
    group.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("action", choices=list(a.lower() for a in dir(Actions) if not a.startswith('_')))

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    ifs = IfState()

    if args.action == Actions.TEMPLATE:
        print(yaml.dump(ifs.template()))

    if args.action in [Actions.CHECK, Actions.CONFIG]:
        parser = YamlParser('./test.yml')
        ifstates = parser.config()

        ifs.update(ifstates)

        if args.action == Actions.CHECK:
            pass
        else:
            ifs.commit()

if __name__ == "__main__":
    main()
