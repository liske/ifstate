from libifstate.util import logger, IfStateLogging

from copy import deepcopy
import logging
import multiprocessing as mp
import os
import re
from setproctitle import setproctitle
import signal

class VrrpFifoProcess(mp.Process):
    '''
    Process for vrrp group/instance configuration.
    '''
    def __init__(self, vrrp_type, vrrp_name, ifstate, log_level):
        self.vrrp_type = vrrp_type
        self.vrrp_name = vrrp_name
        self.ifstate = ifstate
        self.log_level = log_level
        self.queue = mp.Queue()
        super().__init__(target=self.vrrp_worker, name=f'ifstate-vrrp-fifo|{vrrp_type}.{vrrp_name}', daemon=True)

    def vrrp_update(self, vrrp_state):
        self.queue.put(vrrp_state)

    def vrrp_worker(self):
        instance_title = "vrrp-{}-{}".format(self.vrrp_type, self.vrrp_name)
        setproctitle("ifstate-{}".format(instance_title))
        ifslog = IfStateLogging(self.log_level, action=instance_title, log_stderr=False)
        logger.info('worker spawned')
        while True:
            vrrp_state = self.queue.get()
            if vrrp_state is None:
                logger.info('terminating')
                return
            else:
                ifstate = deepcopy(self.ifstate)
                ifstate.apply(self.vrrp_type, self.vrrp_name, vrrp_state)

class VrrpStates():
    '''
    Tracks processes and states for vrrp groups/instances.
    '''
    def __init__(self, ifstate, log_level):
        self.ifstate = ifstate
        self.log_level = log_level
        self.processes = {}
        self.states = {}

    def update(self, vrrp_type, vrrp_name, vrrp_state):
        '''
        Updates the state for a group/instance. A new VrrpFifoProcess is spawned on-demand
        if a group/instance is called the first time.
        '''
        key = (vrrp_type, vrrp_name)
        if not key in self.processes:
            self.processes[key] = VrrpFifoProcess(vrrp_type, vrrp_name, self.ifstate, self.log_level)
            self.processes[key].start()

        self.states[key] = vrrp_state
        self.processes[key].vrrp_update(vrrp_state)

    def reconfigure(self, ifstate):
        '''
        Reconfigure all known groups/instances using their last known state by spawning
        new worker Processes.
        '''
        self.ifstate = ifstate
        for key, state in self.states.items():
            self.processes[key].vrrp_update(None)
            self.processes[key] = VrrpFifoProcess(*key, ifstate, self.log_level)
            self.processes[key].start()
            self.processes[key].vrrp_update(self.states[key])

def vrrp_fifo(args_fifo, ifs_config, log_level):
    vrrp_states = VrrpStates(ifs_config.ifs, log_level)
    ifs_config.set_callback(vrrp_states.reconfigure)

    signal.signal(signal.SIGHUP, ifs_config.sighup_handler)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    pid_file = f"/run/libifstate/vrrp/{os.getpid()}.pid"
    try:
        os.makedirs("/run/libifstate/vrrp", exist_ok=True)

        with open(pid_file, "w", encoding="utf-8") as fh:
            fh.write(args_fifo)
    except IOError as err:
        logger.exception(f'failed to write pid file {pid_file}: {err}')

    try:
        status_pattern = re.compile(
            r'(group|instance) "([^"]+)" (unknown|fault|backup|master)( \d+)?$', re.IGNORECASE)

        with open(args_fifo) as fifo:
            logger.debug("entering fifo loop...")
            for line in fifo:
                m = status_pattern.match(line.strip())
                if m:
                    vrrp_type = m.group(1)
                    vrrp_name = m.group(2)
                    vrrp_state = m.group(3)

                    vrrp_states.update(vrrp_type, vrrp_name, vrrp_state)
                else:
                    logger.warning(f'failed to parse fifo input: {line.strip()}')
                mp.active_children()
    finally:
        try:
            os.remove(pid_file)
        except IOError:
            pass
