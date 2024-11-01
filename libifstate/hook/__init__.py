from libifstate.util import get_run_dir

from pathlib import Path
import pkgutil
from string import Template


HOOK_DIR = '/etc/ifstate/hook.d'
HOOK_WRAPPER = Template(pkgutil.get_data("libifstate", "../hooks/wrapper.sh"))


class Hook():
    def __init__(self, name, script, provides=[], after=[]):
        self.name = name

        if script[0] == '/':
            self.script = Path(script).as_posix()
        else:
            self.script = Path(HOOK_DIR, script).as_posix()

        self.provides = provides
        self.after = after

    def run(self, link):
        run_dir = get_run_dir('hooks', link.idx, self.name)
        wrapper_fn = f"{run_dir}/wrapper.sh"

        with open(wrapper_fn, "w") as fh:
            try:
                fh.write(HOOK_WRAPPER.substitute({
                    'script': self.script,
                    'ifname': link.settings.get('ifname'),
                    'index': link.idx,
                    'netns': link.netns.netns,
                }))
            except KeyError as ex:
                logger.error("Failed to prepare wrapper for hook {}: {}".format(self.name, str(ex)))
        os.chmod(wrapper_fn, 0o700)


class Hooks():
    def __init__(self, ifstate):
        self.hooks = {}
        for hook, opts in ifstate.items():
            if 'script' in opts:
                self.hooks[hook] = Hook(hook, **opts)
            else:
                self.hooks[hook] = Hook(hook, script=hook, **opts)

    def run(self, link, hooks):
        for hook in hooks:
            if not hook in self.hooks:
                logger.warning("Hook {} for {} is unknown!".format(link.settings.get('ifname'), hook))
                continue

            self.hooks[hook].run(link)
