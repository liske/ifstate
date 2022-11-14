from contextlib import contextmanager
import rlcompleter
import atexit
import code
import os
import readline

import pprint
from libifstate.util import ipr

has_pygments = False
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalFormatter

    has_pygments = True
except:
    pass


def pygments_print(obj):
    formated = pprint.pformat(obj)
    print(highlight(formated, PythonLexer(), TerminalFormatter()), end="")


class IfStateConsole(code.InteractiveConsole):
    def __init__(self, locals={}, filename="<ifstate-shell>",
                 histfile=os.path.expanduser("~/.ifstate_history")):

        # use pygments for print() if available
        print_func = pprint.pprint
        if has_pygments:
            print_func = pygments_print

        print("Links:")
        for link in ipr.get_links():
            print("  {:2}: {}".format(
                link.get('index'), link.get_attr('IFLA_IFNAME')))
        print("")


        print("""Symbols:
  ipr = pyroute2.IPRoute()
""")

        locals['ipr'] = ipr
        locals['pprint'] = print_func

        readline.set_completer(rlcompleter.Completer(locals).complete)
        code.InteractiveConsole.__init__(self, locals, filename)

        self.h_len = 0
        self.init_history(histfile)

    def init_history(self, histfile):
        """load history and enable tab completion"""

        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
                self.h_len = readline.get_current_history_length()
            except FileNotFoundError:
                try:
                    open(histfile, 'wb').close()
                except:
                    pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        """append new history entries"""

        new_h_len = readline.get_current_history_length()
        readline.set_history_length(1000)
        readline.append_history_file(new_h_len - self.h_len, histfile)
