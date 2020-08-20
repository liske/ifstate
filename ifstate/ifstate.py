#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.exception import FeatureMissingError, ParserValidationError
from libifstate.util import logger, setup_logging
from collections import namedtuple

import argparse
import logging
import signal
import yaml

class Actions():
    CHECK = "check"
    APPLY = "apply"
    SHOW = "show"

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    group.add_argument("-v", "--verbose", action="store_true", help="be more verbose")
    group.add_argument("-q", "--quiet", action="store_true", help="be more quiet, print only warnings and errors")
    parser.add_argument("-s", "--soft-schema", action="store_true", help="ignore schema validation errors, expect ifstatecli to trigger internal exceptions")
    parser.add_argument("-c", "--config", type=str, default="/etc/ifstate/config.yml", help="configuration YaML filename")
    parser.add_argument("action", choices=list(a.lower() for a in dir(Actions) if not a.startswith('_')), help="specifies the action to perform")

    args = parser.parse_args()
    if args.verbose:
        setup_logging(logging.DEBUG)
    elif args.quiet:
        setup_logging(logging.ERROR)
    else:
        setup_logging(logging.INFO)

    ifs = IfState()

    if args.action == Actions.SHOW:
        # preserve dict order on python 3.7+
        if sys.version_info >= (3,7):
            yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))
        print(yaml.dump(ifs.show()))

    if args.action in [Actions.CHECK, Actions.APPLY]:
        parser = YamlParser(args.config)
        ifstates = parser.config()

        try:
            ifs.update(ifstates, args.soft_schema)
        except FeatureMissingError as ex:
            logger.error("Config uses unavailable feature: {}".format(ex.feature))
            exit(1)
        except ParserValidationError as ex:
            logger.error("Config validation failed for {}".format(ex.detail))
            exit(1)

        if args.action == Actions.CHECK:
            ifs.check()
        else:
            # ignore some well-known signals to prevent interruptions (i.e. due to ssh connection loss)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            ifs.apply()

if __name__ == "__main__":
    main()
