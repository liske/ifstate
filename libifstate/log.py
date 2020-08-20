import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import sys

logger = logging.getLogger('ifstate')

class IfStateLogFilter(logging.Filter):
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
                record.bol = IfStateLogging.ANSI_RED
            elif record.levelno >= logging.WARNING:
                record.bol = IfStateLogging.ANSI_MAGENTA
            else:
                record.bol = ''
            record.eol = IfStateLogging.ANSI_RESET
        else:
            record.bol = ''
            record.eol = ''

        if hasattr(record, 'style'):
            if self.terminal:
                record.style = IfStateLogging.colorize(record.style)
            else:
                record.style = ""
        else:
            record.style = ""

        return True

class IfStateLogging:
    STYLE_OK = "ok"
    STYLE_CHG = "chg"
    STYLE_DEL = "del"

    ANSI_GREEN = "\033[32m"
    ANSI_RED = "\033[31m"
    ANSI_MAGENTA = "\033[35m"
    ANSI_YELLOW = "\033[33m"
    ANSI_RESET = "\033[0m"
    ANSI_BOLD = "\033[1m"

    @staticmethod
    def colorize(style):
        if style == IfStateLogging.STYLE_OK:
            return IfStateLogging.ANSI_GREEN
        if style == IfStateLogging.STYLE_CHG:
            return IfStateLogging.ANSI_YELLOW
        if style == IfStateLogging.STYLE_DEL:
            return IfStateLogging.ANSI_YELLOW
        return ""

    def __init__(self, level, handlers=[]):
        if level != logging.DEBUG:
            sys.tracebacklimit = 0

        logging.basicConfig(
            level=level,
            format='%(bol)s%(prefix)s%(style)s%(message)s%(eol)s',
        )

        f = IfStateLogFilter(sys.stderr.isatty())
        logger.addFilter(f)

        qu = queue.SimpleQueue()
        logger.addHandler(QueueHandler(qu))
        self.listener = QueueListener(qu, *handlers, respect_handler_level=True)
        self.listener.start()

    def quit(self):
        self.listener.stop()
