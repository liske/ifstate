import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import sys

logger = logging.getLogger('ifstate')

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

class LogStyle():
    OK = "ok"
    CHG = "chg"
    DEL = "del"

    @staticmethod
    def colorize(style):
        if style == LogStyle.OK:
            return AnsiColors.GREEN
        if style == LogStyle.CHG:
            return AnsiColors.YELLOW
        if style == LogStyle.DEL:
            return AnsiColors.YELLOW
        return ""

class AnsiColors():
    GREEN = "\033[32m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def setup_logging(level, handlers=[]):
    if level != logging.DEBUG:
        sys.tracebacklimit = 0

    logging.basicConfig(
        level=level,
        format='%(bol)s%(prefix)s%(style)s%(message)s%(eol)s',
    )

    f = LogFilter(sys.stderr.isatty())
    logger.addFilter(f)

    qu = queue.SimpleQueue()
    logger.addHandler(QueueHandler(qu))
    listener = QueueListener(qu, *handlers, respect_handler_level=True)
    listener.start()
