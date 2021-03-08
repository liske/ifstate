#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.exception import FeatureMissingError, LinkNoConfigFound, ParserValidationError, ParserOpenError, ParserIncludeError
from libifstate.util import logger, IfStateLogging
from collections import namedtuple
from copy import deepcopy

import argparse
import logging
import re
import signal
import sys
import yaml


class Actions():
    CHECK = "check"
    APPLY = "apply"
    SHOW = "show"
    SHOWALL = "showall"
    VRRP = "vrrp"
    VRRP_FIFO = "vrrp-fifo"


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
    subparsers = parser.add_subparsers(
        dest='action', required=True, help="specifies the action to perform")

    action_parsers = {
        a.lower().replace("_", "-"): subparsers.add_parser(a.lower().replace("_", "-")) for a in dir(Actions) if not a.startswith('_')
    }

    # Parameters for the vrrp action
    action_parsers[Actions.VRRP].add_argument(
        "type", type=str.lower, choices=["group", "instance"], help="type of vrrp notification")
    action_parsers[Actions.VRRP].add_argument(
        "name", type=str, help="name of the vrrp group or instance")
    action_parsers[Actions.VRRP].add_argument(
        "state", type=str.lower, choices=["unknown", "fault", "backup", "master"], help="the new state for the vrrp group or instance")

    # Parameters for the vrrp-fifo action
    action_parsers[Actions.VRRP_FIFO].add_argument(
        "fifo", type=str, help="named FIFO to read state changes from")

    args = parser.parse_args()
    if args.verbose:
        lvl = logging.DEBUG
    elif args.quiet:
        lvl = logging.ERROR
    else:
        lvl = logging.INFO

    ifslog = IfStateLogging(lvl)
    ifs = IfState()

    if args.action in [Actions.SHOW, Actions.SHOWALL]:
        # preserve dict order on python 3.7+
        if sys.version_info >= (3, 7):
            yaml.add_representer(
                dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))
        print(yaml.dump(ifs.show(args.action == Actions.SHOWALL)))

        ifslog.quit()
        exit(0)

    if args.action in [Actions.CHECK, Actions.APPLY, Actions.VRRP, Actions.VRRP_FIFO]:
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
        elif args.action == Actions.VRRP_FIFO:
            status_pattern = re.compile(
                r'(group|instance) "([^"]+)" (unknown|fault|backup|master)$', re.IGNORECASE)

            with open(args.fifo) as fifo:
                for line in fifo:
                    m = status_pattern.match(line.strip())
                    if m:
                        signal.signal(signal.SIGHUP, signal.SIG_IGN)
                        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
                        signal.signal(signal.SIGTERM, signal.SIG_IGN)
                        try:
                            ifs_tmp = deepcopy(ifs)
                            ifs_tmp.apply(m.group(1), m.group(2), m.group(3))
                        except:
                            pass
        else:
            # ignore some well-known signals to prevent interruptions (i.e. due to ssh connection loss)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                if args.action == Actions.APPLY:
                    ifs.apply()
                elif args.action == Actions.VRRP:
                    ifs.apply(
                        args.type, args.name, args.state)
            except LinkNoConfigFound:
                pass

        ifslog.quit()


if __name__ == "__main__":
    main()
