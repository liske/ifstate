from libifstate.util import logger, IfStateLogging

import atexit
from copy import deepcopy
import logging
import multiprocessing as mp
import threading
import os
import re
from setproctitle import setproctitle
import signal
import subprocess
import sys

class VrrpFifoProcess():
    '''
    Process for vrrp group/instance configuration.
    '''
    def __init__(self, worker_args):
        self.worker_args = worker_args
        self.logger_extra = {'iface': f'{worker_args[-2]} "{worker_args[-1]}"'}
        self.state_queue = mp.Queue()
        self.worker_proc = None

        worker_io = threading.Thread(target=self.dequeue)
        worker_io.start()

    def vrrp_update(self, vrrp_state):
        self.state_queue.put(vrrp_state)

    def dequeue(self):
        while True:
            state = self.state_queue.get()

            # Should we terminate?
            if state is None:
                self.worker_proc.stdin.close()
                self.worker_proc.wait()
                return

            # Restart ifstate vrrp-worker if not alive alive?
            if self.worker_proc.poll() is not None:
                logger.warning("worker died", extra=self.logger_extra)
                self.start()

            logger.info(f'state => {state}', extra=self.logger_extra)
            self.worker_proc.stdin.write(f'{state}\n')
            self.worker_proc.stdin.flush()
        logger.warning("dequeue terminated")

    def start(self):
        logger.info("spawning worker", extra=self.logger_extra)
        self.worker_proc = subprocess.Popen(self.worker_args, stdin=subprocess.PIPE, stderr=sys.stderr, text=True)


class VrrpStates():
    '''
    Tracks processes and states for vrrp groups/instances.
    '''
    def __init__(self, ifs_config):
        self.ifs_config = ifs_config
        self.processes = {}
        self.states = {}
        self.pid_file = f"/run/libifstate/vrrp/{os.getpid()}.pid"
        self.cfg_file = f"/run/libifstate/vrrp/{os.getpid()}.cfg"
        self.worker_args = (
            sys.argv[0],
            '-c', self.cfg_file,
            'vrrp-worker')
        if logger.level == logging.DEBUG:
            self.worker_args.append('-v')

    def update(self, vrrp_type, vrrp_name, vrrp_state):
        '''
        Updates the state for a group/instance. A new VrrpFifoProcess is spawned on-demand
        if a group/instance is called the first time.
        '''
        key = (vrrp_type, vrrp_name)
        if not key in self.processes:
            worker_args = self.worker_args + key
            self.processes[key] = VrrpFifoProcess(worker_args)
            self.processes[key].start()

        self.states[key] = vrrp_state
        self.processes[key].vrrp_update(vrrp_state)

    def reconfigure(self, *argv):
        '''
        Reconfigure all known groups/instances using their last known state by spawning
        new worker Processes.
        '''

        # save new config to temp file
        try:
            self.ifs_config.load_config()
            self.ifs_config.dump_config(self.cfg_file)
        except Exception as ex:
            logger.error(f'failed to reload config: {ex}')
            return

        for key, state in self.states.items():
            worker_args = self.worker_args + key
            self.processes[key].vrrp_update(None)
            self.processes[key] = VrrpFifoProcess(worker_args)
            self.processes[key].start()
            self.processes[key].vrrp_update(self.states[key])

    def cleanup_run(self, *argv):
        """
        """
        for file in [self.pid_file, self.cfg_file]:
            try:
                os.unlink(file)
            except OSError as ex:
                if ex.errno != 2:
                    logger.warning(f"cannot cleanup {file}: {ex}")

def vrrp_fifo(args_fifo, ifs_config):
    vrrp_states = VrrpStates(ifs_config)

    signal.signal(signal.SIGHUP, vrrp_states.reconfigure)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, vrrp_states.cleanup_run)

    try:
        os.makedirs("/run/libifstate/vrrp", exist_ok=True)

        with open(vrrp_states.pid_file, "w", encoding="utf-8") as fh:
            fh.write(args_fifo)
        atexit.register(vrrp_states.cleanup_run)

        ifs_config.dump_config(vrrp_states.cfg_file)
    except IOError as err:
        logger.exception(f'failed to write pid file {vrrp_states.pid_file}: {err}')

    try:
        status_pattern = re.compile(
            r'(group|instance) "([^"]+)" (unknown|fault|backup|master|stop)( \d+)?$', re.IGNORECASE)

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
        vrrp_states.cleanup_run()

def vrrp_worker(vrrp_type, vrrp_name, ifs_config):
    instance_title = "vrrp-{}-{}".format(vrrp_type, vrrp_name)
    setproctitle("ifstate-{}".format(instance_title))

    logger.info('worker is alive')
    for state in sys.stdin:
        vrrp_state = state.strip()

        ifstate = deepcopy(ifs_config.ifs)
        ifstate.apply(vrrp_type, vrrp_name, vrrp_state)
    logger.info('terminating')
