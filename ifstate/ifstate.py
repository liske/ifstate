#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.exception import FeatureMissingError, LinkNoConfigFound, ParserValidationError, ParserOpenError, ParserIncludeError
from libifstate.util import logger, IfStateLogging
from collections import namedtuple

import argparse
import logging
import signal
import sys
import yaml


class Actions():
    CHECK = "check"
    APPLY = "apply"
    SHOW = "show"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    group.add_argument("-v", "--verbose", action="store_true",
                       help="be more verbose")
    group.add_argument("-q", "--quiet", action="store_true",
                       help="be more quiet, print only warnings and errors")
    parser.add_argument("-s", "--soft-schema", action="store_true",
                        help="ignore schema validation errors, expect ifstatecli to trigger internal exceptions")
    parser.add_argument("-c", "--config", type=str,
                        default="/etc/ifstate/config.yml", help="configuration YaML filename")
    parser.add_argument("action", choices=list(a.lower() for a in dir(
        Actions) if not a.startswith('_')), help="specifies the action to perform")

    args = parser.parse_args()
    if args.verbose:
        lvl = logging.DEBUG
    elif args.quiet:
        lvl = logging.ERROR
    else:
        lvl = logging.INFO

    ifslog = IfStateLogging(lvl)
    ifs = IfState()

    if args.action == Actions.SHOW:
        # preserve dict order on python 3.7+
        if sys.version_info >= (3, 7):
            yaml.add_representer(
                dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))
        print(yaml.dump(ifs.show()))

        ifslog.quit()
        exit(0)

    if args.action in [Actions.CHECK, Actions.APPLY]:
        try:
            parser = YamlParser(args.config)
        except ParserOpenError as ex:
            logger.error(
                "Config loading from {} failed: {}".format(ex.fn, ex.msg))
            ifslog.quit()
            exit(1)
        except yaml.parser.ParserError as ex:
            logger.error("Config parsing failed:\n\n{}".format(str(ex)))
            ifslog.quit()
            exit(2)
        except ParserIncludeError as ex:
            logger.error(
                "Config include file {} failed: {}".format(ex.fn, ex.msg))
            ifslog.quit()
            exit(3)

        try:
            ifstates = parser.config()
            ifs.update(ifstates, args.soft_schema)
        except ParserValidationError as ex:
            logger.error("Config validation failed for {}".format(ex.detail))
            ifslog.quit()
            exit(4)
        except FeatureMissingError as ex:
            logger.error(
                "Config uses unavailable feature: {}".format(ex.feature))
            ifslog.quit()
            exit(5)

        if args.action == Actions.CHECK:
            try:
                ifs.check()
            except LinkNoConfigFound:
                pass
        else:
            # ignore some well-known signals to prevent interruptions (i.e. due to ssh connection loss)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                ifs.apply()
            except LinkNoConfigFound:
                pass

        ifslog.quit()


if __name__ == "__main__":
    main()
