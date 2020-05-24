import logging
from pyroute2 import IPRoute

logger = logging.getLogger('ifstate')
ipr = IPRoute()

class LogStyle():
    OK = "ok"
    CHG = "chg"
    DEL = "del"

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
