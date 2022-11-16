from libifstate.util import logger, IfStateLogging
from ctypes import cdll, Structure, POINTER, c_int, c_uint, c_char_p, c_size_t, c_bool, c_void_p, c_ubyte, c_ulong, c_char
import ctypes
import os
import shutil


BPF_PROG_TYPE_XDP = 6

bpfs_ifstate_dir = '/sys/fs/bpf/ifstate'


class struct_bpf_link(Structure):
    pass


class struct_bpf_object(Structure):
    pass


class struct_bpf_object_open_opts(Structure):
    _fields_ = [
        ('sz', c_size_t),
        ('object_name', c_char_p),
        ('relaxed_maps', c_bool),
        ('pin_root_path', c_char_p),
        ('unnamed_1', c_uint),
        ('kconfig', c_char_p),
        ('btf_custom_path', c_char_p),
        ('kernel_log_buf', c_char_p),
        ('kernel_log_size', c_size_t),
        ('kernel_log_level', c_uint),
        ('unnamed_2', c_size_t),
    ]


class struct_bpf_prog_info(Structure):
    _fields_ = [
        ('type', c_uint),
        ('id', c_uint),
        ('tag', c_ubyte * int(8)),
        ('jited_prog_len', c_uint),
        ('xlated_prog_len', c_uint),
        ('jited_prog_insns', c_ulong),
        ('xlated_prog_insns', c_ulong),
        ('load_time', c_ulong),
        ('created_by_uid', c_uint),
        ('nr_map_ids', c_uint),
        ('map_ids', c_ulong),
        ('name', c_char * int(16)),
        ('ifindex', c_uint),
        ('gpl_compatible', c_uint, 1),
        ('unnamed_1', c_uint, 31),
        ('netns_dev', c_ulong),
        ('netns_ino', c_ulong),
        ('nr_jited_ksyms', c_uint),
        ('nr_jited_func_lens', c_uint),
        ('jited_ksyms', c_ulong),
        ('jited_func_lens', c_ulong),
        ('btf_id', c_uint),
        ('func_info_rec_size', c_uint),
        ('func_info', c_ulong),
        ('nr_func_info', c_uint),
        ('nr_line_info', c_uint),
        ('line_info', c_ulong),
        ('jited_line_info', c_ulong),
        ('nr_jited_line_info', c_uint),
        ('line_info_rec_size', c_uint),
        ('jited_line_info_rec_size', c_uint),
        ('nr_prog_tags', c_uint),
        ('prog_tags', c_ulong),
        ('run_time_ns', c_ulong),
        ('run_cnt', c_ulong),
        ('recursion_misses', c_ulong),
        ('verified_insns', c_uint),
    ]


class struct_bpf_program(Structure):
    pass


# check if libbpf.so.1 is available
libbpf = None
try:
    libbpf = cdll.LoadLibrary('libbpf.so.1')
except OSError:
    # ignore missing library
    raise ModuleNotFoundError("Failed to load library libbpf.so.1!")


libbpf.bpf_object__open_file.argtypes = (
    c_char_p,                               # const char *path
    POINTER(struct_bpf_object_open_opts),   # struct bpf_object_open_opts *opts
)
libbpf.bpf_object__open_file.restype = POINTER(struct_bpf_object)

libbpf.bpf_object__pin_maps.argtypes = (
    POINTER(struct_bpf_object),     # struct bpf_object *obj
    c_char_p,                       # const char *path
)
libbpf.bpf_object__pin_maps.restype = c_int

libbpf.bpf_program__attach_xdp.argtypes = (
    POINTER(struct_bpf_program),    # const struct bpf_program *prog
    c_int,                          # int ifindex
)
libbpf.bpf_program__attach_xdp.restype = POINTER(struct_bpf_link)

libbpf.bpf_object__next_program.argtypes = (
    POINTER(struct_bpf_object),     # const struct bpf_object *obj
    POINTER(struct_bpf_program),    # struct bpf_program *prog
)
libbpf.bpf_object__next_program.restype = POINTER(struct_bpf_program)

libbpf.bpf_program__section_name.argtypes = (
    POINTER(struct_bpf_program),    # const struct bpf_program *prog
)
libbpf.bpf_program__section_name.restype = c_char_p

libbpf.bpf_obj_get.argtypes = (
    c_char_p,   # const const char *pathname
)
libbpf.bpf_obj_get.restype = c_int

libbpf.bpf_object__load.argtypes = (
    POINTER(struct_bpf_object),     # const struct bpf_object *obj
)
libbpf.bpf_object__load.restype = c_int

libbpf.bpf_object__name.argtypes = (
    POINTER(struct_bpf_object),     # const struct bpf_object *obj
)
libbpf.bpf_object__name.restype = c_char_p

libbpf.bpf_link__pin.argtypes = (
    POINTER(struct_bpf_link),   # const struct bpf_link *link
    c_char_p,                   # const char *path
)
libbpf.bpf_link__pin.restype = c_int


libbpf.bpf_program__fd.argtypes = (
    POINTER(struct_bpf_program),    # const struct bpf_program *prog
)
libbpf.bpf_program__fd.restype = c_int

libbpf.bpf_program__pin.argtypes = (
    POINTER(struct_bpf_program),    # struct bpf_program *prog
    c_char_p,                       # const char *path
)
libbpf.bpf_program__pin.restype = c_int

libbpf.bpf_prog_get_fd_by_id.argtypes = (
    c_uint,     # c_uint id
)
libbpf.bpf_prog_get_fd_by_id.restype = c_int

libbpf.bpf_obj_get_info_by_fd.argtypes = (
    c_int,      # int bpf_fd
    c_void_p,   # void *info
    POINTER(c_uint),   # c_uint *info_len
)
libbpf.bpf_obj_get_info_by_fd.restype = c_int


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
        progs_pin_dir = "{}/bpf/progs".format(bpfs_ifstate_dir)
        maps_pin_dir = "{}/bpf/maps".format(bpfs_ifstate_dir)
        pinning = False
        if os.path.isdir('/sys/fs/bpf'):
            pinning = True

            if do_apply:
                os.makedirs(progs_pin_dir, exist_ok=True)
                os.makedirs(maps_pin_dir, exist_ok=True)
        else:
            logger.debug('bpfs is not mounted, skipping maps pinning')

        # load (and pin) bpf programs
        for name, config in self.bpf_progs.items():
            current_prog_tag = None
            current_prog_fd = -1
            self.bpf_tags[name] = None
            self.bpf_fds[name] = -1

            prog_pin_filename = "{}/{}".format(progs_pin_dir, name)
            if os.path.isfile(prog_pin_filename):
                current_prog_fd = libbpf.bpf_obj_get( os.fsencode(prog_pin_filename) )

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
            else:
                logger.warning(
                    'BPF failed to get prog info on {}'.format(name))

    def get_bpf(self, name):
        return (self.bpf_fds.get(name, -1), self.bpf_tags.get(name))
