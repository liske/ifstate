import logging
from logging.handlers import QueueHandler, QueueListener
import os
import queue
import sys

logger = logging.getLogger('ifstate')
logger.propagate = False
logger.log_add = lambda option, oper='add': logger.info(oper, extra={'option': option, 'style': IfStateLogging.STYLE_CHG})
logger.log_change = lambda option, oper='change': logger.info(oper, extra={'option': option, 'style': IfStateLogging.STYLE_CHG})
logger.log_ok = lambda option, oper='ok': logger.info(oper, extra={'option': option, 'style': IfStateLogging.STYLE_OK})
logger.log_del = lambda option, oper='del': logger.info(oper, extra={'option': option, 'style': IfStateLogging.STYLE_DEL})

formatter = logging.Formatter('%(bol)s%(prefix)s%(style)s%(message)s%(eol)s')

class IfStateLogFilter(logging.Filter):
    def __init__(self, is_terminal):
        super().__init__()
        self.is_terminal = is_terminal

    def filter(self, record):
        record.levelshort = record.levelname[:1]

        if hasattr(record, 'iface'):
            record.prefix = " {:35} ".format(record.iface)
        else:
            record.prefix = ''

        if hasattr(record, 'option'):
            record.prefix = "   {:33} ".format(record.option)

        if self.is_terminal and record.levelno >= logging.WARNING:
            if record.levelno >= logging.ERROR:
                record.bol = IfStateLogging.ANSI_RED
            else:
                record.bol = IfStateLogging.ANSI_MAGENTA
            record.eol = IfStateLogging.ANSI_RESET
        else:
            record.bol = ''
            record.eol = ''

        if self.is_terminal and hasattr(record, 'style'):
            record.style = IfStateLogging.colorize(record.style)
            record.eol = IfStateLogging.ANSI_RESET
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

    def __init__(self, level, handlers=[], action=None):
        if level != logging.DEBUG:
            sys.tracebacklimit = 0

        logging.basicConfig(
            level=level,
        )

        has_stderr = sys.stderr is not None
        is_terminal = has_stderr and sys.stderr.isatty()

        # add custom logging handlers
        if not handlers:
            handlers = []

            if has_stderr:
                # log to stderr
                stream = logging.StreamHandler(sys.stderr)
                stream.addFilter(IfStateLogFilter(is_terminal))
                stream.setFormatter(formatter)
                handlers.append(stream)

            # log to syslog
            syslog = logging.handlers.SysLogHandler('/dev/log', facility=logging.handlers.SysLogHandler.LOG_DAEMON)
            if action is None:
                syslog.ident = 'ifstate[{}] '.format(os.getpid())
            else:
                syslog.ident = 'ifstate-{}[{}] '.format(action, os.getpid())
            syslog.addFilter(IfStateLogFilter(False))
            syslog.setFormatter(formatter)
            handlers.append(syslog)

        qu = queue.SimpleQueue()
        queue_handler = QueueHandler(qu)
        queue_handler.setLevel(level)
        logger.addHandler(queue_handler)
        self.listener = QueueListener(
            qu, *handlers, respect_handler_level=True)
        self.listener.start()

    def quit(self):
        self.listener.stop()
