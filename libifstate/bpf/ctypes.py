from ctypes import cdll, Structure, POINTER, c_int, c_uint, c_char_p, c_size_t, c_bool, c_void_p, c_ubyte, c_ulong, c_char
import ctypes


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

libbpf.bpf_program__fd.argtypes = (
    POINTER(struct_bpf_program),    # const struct bpf_program *prog
)
libbpf.bpf_program__fd.restype = c_int

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
