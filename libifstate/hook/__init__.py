from libifstate.util import get_run_dir
from libifstate.util import logger

from pathlib import Path
import os
import pkgutil
from shlex import quote
from string import Template


HOOK_DIR = '/etc/ifstate/hook.d'
HOOK_WRAPPER = Template(pkgutil.get_data("libifstate", "../hooks/wrapper.sh").decode("utf-8"))

class Hook():
    def __init__(self, name, script, provides=[], after=[]):
        self.name = name

        if script[0] == '/':
            self.script = Path(script).as_posix()
        else:
            self.script = Path(HOOK_DIR, script).as_posix()

        self.provides = provides
        self.after = after

    def run(self, link, args, action):
        run_dir = get_run_dir('hooks', str(link.idx), self.name)
        wrapper_fn = f"{run_dir}/wrapper.sh.new"

        with open(wrapper_fn, "w") as fh:
            template_vars = {
                    'script': self.script,
                    'ifname': link.settings.get('ifname'),
                    'index': link.idx,
                    'netns': '',
                    'vrf': '',
                    'rundir': run_dir,
                }

            if link.netns.netns:
                template_vars['netns'] = link.netns.netns

            if link.get_if_attr('IFLA_INFO_SLAVE_KIND') == 'vrf':
                template_vars['vrf'] = link.settings.get('master')

            args_list = []
            for k, v in args.items():
                args_list.append(f'export IFS_ARGS_{k.upper()}={quote(v)}')
            template_vars['args'] = "\n".join(args_list)

            try:
                fh.write(HOOK_WRAPPER.substitute(template_vars))
            except KeyError as ex:
                logger.error("Failed to prepare wrapper for hook {}: variable {} unknown".format(self.name, str(ex)))
                next
            except ValueError as ex:
                logger.error("Failed to prepare wrapper for hook {}: {}".format(self.name, str(ex)))
                next
        os.chmod(wrapper_fn, 0o700)


class Hooks():
    def __init__(self, ifstate):
        self.hooks = {}
        for hook, opts in ifstate.items():
            if 'script' in opts:
                self.hooks[hook] = Hook(hook, **opts)
            else:
                self.hooks[hook] = Hook(hook, script=hook, **opts)

    def run(self, link, do_apply):
        if do_apply:
            action = "start"
        else:
            action = "check"

        for hook in link.hooks:
            if not hook["name"] in self.hooks:
                logger.warning("Hook {} for {} is unknown!".format(link.settings.get('ifname'), hook))
                continue

            self.hooks[hook["name"]].run(link, hook.get('args', {}), action)
