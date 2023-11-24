#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.exception import FeatureMissingError, LinkNoConfigFound, LinkCircularLinked, ParserValidationError, ParserOpenError, ParserParseError, ParserIncludeError
from libifstate.util import logger, IfStateLogging
from collections import namedtuple
from copy import deepcopy
from setproctitle import setproctitle

import argparse
import glob
import logging
import os
from pathlib import Path
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
    SHELL = "shell"

ACTIONS_HELP = {
    "CHECK"    : "dry run update the network config",
    "APPLY"    : "update the network config",
    "SHOW"     : "show running network config",
    "SHOWALL"  : "show running network config (more settings)",
    "VRRP"     : "run as keepalived notify script",
    "VRRP_FIFO": "run as keepalived notify_fifo_script",
    "SHELL"    : "launch interactive python shell (pyroute2)",
}

class IfsConfigHandler():
    def __init__(self, fn, soft_schema):
        self.fn = fn
        self.soft_schema = soft_schema

        self.ifs = self.load_config()

    def sighup_handler(self, signum, frame):
        logger.info("SIGHUP: reloading configuration")
        try:
            self.ifs = self.load_config()
        except:
            logger.exception("failed to reload configuration")

    def load_config(self):
        try:
            parser = YamlParser(self.fn)
        except ParserOpenError as ex:
            logger.error(
                "Config loading from {} failed: {}".format(ex.fn, ex.msg))
            raise ex
        except ParserParseError as ex:
            logger.error("Config parsing failed:\n\n{}".format(str(ex)))
            raise ex
        except ParserIncludeError as ex:
            logger.error(
                "Config include file {} failed: {}".format(ex.fn, ex.msg))
            raise ex

        try:
            ifstates = parser.config()

            ifs = IfState()
            ifs.update(ifstates, self.soft_schema)
            return ifs
        except ParserValidationError as ex:
            logger.error("Config validation failed for {}".format(ex.detail))
            raise ex
        except FeatureMissingError as ex:
            logger.error(
                "Config uses unavailable feature: {}".format(ex.feature))
            raise ex


def shell():
    from ifstate.shell import IfStateConsole
    import pyroute2

    shell = IfStateConsole()
    shell.interact(banner=f"ifstate {__version__}; pyroute2 {pyroute2.__version__}")


def sighup_vrrp_fifo():
    prefix = 'ifstate-vrrp-fifo@'
    pids = {}

    for pid_file in glob.glob('/run/libifstate/vrrp/[1-9]*.pid'):
        pid = Path(pid_file).stem
        if pid.isnumeric():
            try:
                with open(f'/proc/{pid}/cmdline', encoding='utf-8') as fh:
                    if prefix == fh.read(len(prefix)):
                        # send SIGHUP to reload config
                        os.kill(int(pid), signal.SIGHUP)

                        pids[pid] = fh.read(32)
            except OSError:
                pass

    if len(pids):
        logger.info("")
        logger.info("notified vrrp-fifo handlers...")
        for pid, fifo in sorted(pids.items()):
            logger.info(fifo, extra={'option': pid, 'style': IfStateLogging.STYLE_CHG})

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
        a.lower().replace("_", "-"): subparsers.add_parser(a.lower().replace("_", "-"), help=ACTIONS_HELP[a]) for a in dir(Actions) if not a.startswith('_')
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

    if args.action == Actions.VRRP_FIFO:
        setproctitle("ifstate-{}@{}".format(args.action, args.fifo))
    else:
        setproctitle("ifstate-{}".format(args.action))

    if args.action == Actions.SHELL:
        shell()
        exit(0)

    ifslog = IfStateLogging(lvl, action=args.action)

    if args.action in [Actions.SHOW, Actions.SHOWALL]:
        # preserve dict order on python 3.7+
        if sys.version_info >= (3, 7):
            yaml.add_representer(
                dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))
        ifs = IfState()
        print(yaml.dump(ifs.show(args.action == Actions.SHOWALL)))

        ifslog.quit()
        exit(0)

    if args.action in [Actions.CHECK, Actions.APPLY, Actions.VRRP, Actions.VRRP_FIFO]:
        try:
            ifs_config = IfsConfigHandler(args.config, args.soft_schema)
        except (ParserOpenError,
                ParserParseError,
                ParserIncludeError,
                ParserValidationError,
                FeatureMissingError) as ex:
            ifslog.quit()
            exit(ex.exit_code())

        if args.action == Actions.CHECK:
            try:
                ifs_config.ifs.check()
            except LinkNoConfigFound:
                pass
            except LinkCircularLinked as ex:
                ifslog.quit()
                exit(ex.exit_code())
        elif args.action == Actions.VRRP_FIFO:
            signal.signal(signal.SIGHUP, ifs_config.sighup_handler)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            pid_file = f"/run/libifstate/vrrp/{os.getpid()}.pid"
            try:
                os.makedirs("/run/libifstate/vrrp", exist_ok=True)

                with open(pid_file, "w", encoding="utf-8") as fh:
                    fh.write(args.fifo)
            except:
                logger.exception("failed to write pid file f{pid_file}")

            try:
                status_pattern = re.compile(
                    r'(group|instance) "([^"]+)" (unknown|fault|backup|master)( \d+)?$', re.IGNORECASE)

                with open(args.fifo) as fifo:
                    for line in fifo:
                        m = status_pattern.match(line.strip())
                        if m:
                            try:
                                ifs_tmp = deepcopy(ifs_config.ifs)
                                ifs_tmp.apply(m.group(1), m.group(2), m.group(3))
                            except:
                                logger.exception("failed to apply state change")
            finally:
                try:
                    os.remove(pid_file)
                except:
                    pass
        else:
            # ignore some well-known signals to prevent interruptions (i.e. due to ssh connection loss)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                if args.action == Actions.APPLY:
                    ifs_config.ifs.apply()
                    sighup_vrrp_fifo()
                elif args.action == Actions.VRRP:
                    ifs_config.ifs.apply(
                        args.type, args.name, args.state)
            except LinkNoConfigFound:
                pass
            except LinkCircularLinked as ex:
                ifslog.quit()
                exit(ex.exit_code())

        ifslog.quit()


if __name__ == "__main__":
    main()
