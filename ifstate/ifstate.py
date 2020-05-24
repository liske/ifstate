#!/usr/bin/env python3

from libifstate.parser import YamlParser
from libifstate import __version__, IfState
from libifstate.util import logger, LogStyle , AnsiColors
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

class LogFilter(logging.Filter):
    def __init__(self, terminal):
        super().__init__()
        self.terminal = terminal

    def filter(self, record):
        record.levelshort = record.levelname[:1]
        if hasattr(record, 'iface'):
            record.prefix = " {:15} ".format(record.iface)
        else:
            record.prefix = ''

        if self.terminal:
            if record.levelno >= logging.ERROR:
                record.bol = AnsiColors.RED
            elif record.levelno >= logging.WARNING:
                record.bol = AnsiColors.MAGENTA
            else:
                record.bol = ''
            record.eol = AnsiColors.RESET
        else:
            record.bol = ''
            record.eol = ''

        if hasattr(record, 'style'):
            if self.terminal:
                record.style = LogStyle.colorize(record.style)
            else:
                record.style = ""
        else:
            record.style = ""

        return True

def setup_logging(level):
    if level != logging.DEBUG:
        sys.tracebacklimit = 0

    logging.basicConfig(
        level=level,
        format='%(bol)s%(prefix)s%(style)s%(message)s%(eol)s',
    )

    f = LogFilter(sys.stderr.isatty())
    logger.addFilter(f)

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

        ifs.update(ifstates)

        if args.action == Actions.CHECK:
            pass
        else:
            # ignore some well-known signals to prevent interruptions (i.e. due to ssh connection loss)
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            ifs.apply()

if __name__ == "__main__":
    main()
