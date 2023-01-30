from libifstate.util import logger, IfStateLogging
from libifstate.bpf.map import BPF_Map
from libifstate.bpf.ctypes import *
import os
import shutil


BPF_PROG_TYPE_XDP = 6

bpfs_ifstate_dir = '/sys/fs/bpf/ifstate'


class BPF():
    def __init__(self):
        self.bpf_fds = {}
        self.bpf_progs = {}
        self.bpf_tags = {}

    def add(self, name, config):
        self.bpf_progs[name] = config

    def apply(self, do_apply):
        logger.info('\nloading BPF programs...')

        # prepare pinning directories
        progs_pin_dir = "{}/progs".format(bpfs_ifstate_dir)
        maps_pin_dir = "{}/maps".format(bpfs_ifstate_dir)
        pinning = False
        if os.path.ismount('/sys/fs/bpf'):
            logger.debug('bpfs is mounted, enable pinning')
            pinning = True

            if do_apply:
                os.makedirs(progs_pin_dir, exist_ok=True)
                os.makedirs(maps_pin_dir, exist_ok=True)
        else:
            logger.debug('bpfs is not mounted, skipping pinning')

        # load (and pin) bpf programs
        for name, config in self.bpf_progs.items():
            current_prog_tag = None
            current_prog_fd = -1
            self.bpf_tags[name] = None
            self.bpf_fds[name] = -1

            prog_pin_filename = "{}/{}".format(progs_pin_dir, name)
            if os.path.isfile(prog_pin_filename):
                current_prog_fd = libbpf.bpf_obj_get(
                    os.fsencode(prog_pin_filename))

                if current_prog_fd < 0:
                    logger.warning('could not get current BPF obj fd for {}: {}'.format(
                        name, os.strerror(-current_prog_fd)))
                else:
                    self.bpf_fds[name] = current_prog_fd

                    current_prog_info = struct_bpf_prog_info()
                    current_prog_size = ctypes.c_uint(
                        ctypes.sizeof(current_prog_info))
                    rc = libbpf.bpf_obj_get_info_by_fd(current_prog_fd, ctypes.byref(
                        current_prog_info), ctypes.byref(current_prog_size))
                    if rc == 0:
                        current_prog_tag = bytes(current_prog_info.tag).hex()
                        self.bpf_tags[name] = current_prog_tag

                        logger.debug('current prog tag: {}'.format(current_prog_tag), extra={
                            'iface': name})
                    else:
                        logger.warning('could not get current BPF obj info for {}: {}'.format(
                            name, os.strerror(-rc)))

            # load new BPF prog
            new_prog_tag = None
            new_prog_fd = None

            new_obj = libbpf.bpf_object__open_file(
                os.fsencode(config["object"]),
                None,
            )
            if not new_obj:
                logger.warning('BPF open on {} failed: {}'.format(
                    name, os.strerror(ctypes.get_errno())))
                continue

            logger.debug('loaded object: {}'.format(libbpf.bpf_object__name(new_obj).decode('ascii')), extra={
                'iface': name})

            rc = libbpf.bpf_object__load(new_obj)
            if rc < 0:
                logger.warning('BPF load on {} failed: {}'.format(
                    name, os.strerror(-rc)))
                continue

            new_prog = libbpf.bpf_object__next_program(new_obj, None)
            while new_prog:
                section = libbpf.bpf_program__section_name(
                    new_prog).decode('ascii')

                logger.debug('  section: {}'.format(section), extra={
                    'iface': name})

                if section == config['section']:
                    break
                prog = libbpf.bpf_object__next_program(new_obj, new_prog)

            if not new_prog:
                logger.warning('BPF section {} on {} not found'.format(
                    config['section'], name))
                continue

            # get prog fd
            new_prog_fd = libbpf.bpf_program__fd(new_prog)
            if not new_prog_fd:
                logger.warning('BPF failed to get prog fd on {}'.format(
                    name))
                continue

            # get new prog tag
            info = struct_bpf_prog_info()
            sz = ctypes.c_uint(ctypes.sizeof(info))
            rc = libbpf.bpf_obj_get_info_by_fd(
                new_prog_fd, ctypes.byref(info), ctypes.byref(sz))
            if rc == 0:
                new_prog_tag = bytes(info.tag).hex()

                logger.debug('new prog tag: {}'.format(new_prog_tag), extra={
                    'iface': name})

                if current_prog_tag != new_prog_tag:
                    self.bpf_fds[name] = new_prog_fd
                    self.bpf_tags[name] = new_prog_tag

                    if os.path.isfile(prog_pin_filename):
                        os.unlink(prog_pin_filename)
                    libbpf.bpf_program__pin(
                        new_prog,
                        os.fsencode(prog_pin_filename))

                    maps_path = "{}/{}".format(maps_pin_dir, name)

                    # unbind any orphan maps
                    if os.path.isdir(maps_path):
                        shutil.rmtree(maps_path)

                    # create a new maps directory
                    os.makedirs(maps_path, exist_ok=True)

                    # pin  maps
                    logger.debug('pin maps at: {}'.format(maps_path), extra={
                        'iface': name})
                    libbpf.bpf_object__pin_maps(
                        new_obj,
                        os.fsencode(maps_path))

                    logger.info(
                        'change',
                        extra={'iface': name, 'style': IfStateLogging.STYLE_CHG})
                else:
                    logger.info(
                        'ok',
                        extra={'iface': name, 'style': IfStateLogging.STYLE_OK})

                # update maps if appropriate
                if config.get('maps'):
                    for map_name, map_entries in config['maps'].items():
                        map_filename = "{}/{}/{}".format(maps_pin_dir, name, map_name)

                        try:
                            map_instance = BPF_Map(map_filename)
                        except OSError as ex:
                            logger.warning(
                                "opening bpf map {} failed: {}".format(map_name, ex))
                            continue

                        # TODO: support to manage map entries
            else:
                logger.warning(
                    'BPF failed to get prog info on {}'.format(name))

    def get_bpf(self, name):
        return (self.bpf_fds.get(name, -1), self.bpf_tags.get(name))
