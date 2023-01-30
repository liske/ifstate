#
# The code in this file is mostly based on the Python package pybpfmaps by Peter Scholz
# which is distributed under the Apache 2.0 license.
#
#   https://github.com/PeterStolz/pybpfmaps
#

import ctypes
import os
import time
from enum import IntEnum
from libifstate.bpf.ctypes import libbpf

BPF_OBJ_NAME_LEN = 16


class Bpf_prog_info(ctypes.Structure):
    # info struct def https://github.com/torvalds/linux/blob/b4a5ea09b29371c2e6a10783faa3593428404343/tools/include/uapi/linux/bpf.h#L5880
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
        ("tag", ctypes.c_uint8),
        ("jited_prog_len", ctypes.c_uint32),
        ("xlated_prog_len", ctypes.c_uint32),
        ("jited_prog_insns", ctypes.c_uint64),
        ("xlated_prog_insns", ctypes.c_uint64),
        ("load_time", ctypes.c_uint64),
        ("created_by_uid", ctypes.c_uint32),
        ("nr_map_ids", ctypes.c_uint32),
        ("map_ids", ctypes.c_uint64),
        ("name", ctypes.c_char * BPF_OBJ_NAME_LEN),
        ("ifindex", ctypes.c_uint32),
        ("gpl_compatible:1", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("netns_dev", ctypes.c_uint64),
        ("netns_ino", ctypes.c_uint64),
        ("nr_jited_ksyms", ctypes.c_uint32),
        ("nr_jited_func_lens", ctypes.c_uint32),
        ("jited_ksyms", ctypes.c_uint64),
        ("jited_func_lens", ctypes.c_uint64),
        ("btf_id", ctypes.c_uint32),
        ("func_info_rec_size", ctypes.c_uint32),
        ("func_info", ctypes.c_uint64),
        ("nr_func_info", ctypes.c_uint32),
        ("nr_line_info", ctypes.c_uint32),
        ("line_info", ctypes.c_uint64),
        ("jited_line_info", ctypes.c_uint64),
        ("nr_jited_line_info", ctypes.c_uint32),
        ("line_info_rec_size", ctypes.c_uint32),
        ("jited_line_info_rec_size", ctypes.c_uint32),
        ("nr_prog_tags", ctypes.c_uint32),
        ("prog_tags", ctypes.c_uint64),
        ("run_time_ns", ctypes.c_uint64),
        ("run_cnt", ctypes.c_uint64),
        ("recursion_misses", ctypes.c_uint64),
        ("verified_insns", ctypes.c_uint32),
    ]


class Bpf_map_info(ctypes.Structure):
    # info struct def https://github.com/torvalds/linux/blob/b4a5ea09b29371c2e6a10783faa3593428404343/tools/include/uapi/linux/bpf.h#L5880
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
        ("key_size", ctypes.c_uint32),
        ("value_size", ctypes.c_uint32),
        ("max_entries", ctypes.c_uint32),
        ("map_flags", ctypes.c_uint32),
        ("name", ctypes.c_char * BPF_OBJ_NAME_LEN),
        ("ifindex", ctypes.c_uint32),
        ("btf_vmlinux_value_type_id", ctypes.c_uint32),
        ("netns_dev", ctypes.c_uint64),
        ("netns_ino", ctypes.c_uint64),
        ("btf_id", ctypes.c_uint32),
        ("btf_key_type_id", ctypes.c_uint32),
        ("btf_value_type_id", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("map_extra", ctypes.c_uint64),
    ]


class Bpf_map_struct(ctypes.Structure):
    """
    enum bpf_map_type map_type;
    __u32 key_size;
    __u32 value_size;
    __u32 max_entries;
    __u32 id;
    """

    _fields_ = [
        ("map_type", ctypes.c_uint32),
        ("key_size", ctypes.c_uint32),
        ("value_size", ctypes.c_uint32),
        ("max_entries", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
    ]


class MapTypes(IntEnum):
    BPF_MAP_TYPE_HASH = 1
    BPF_MAP_TYPE_ARRAY = 2
    BPF_MAP_TYPE_PROG_ARRAY = 3
    BPF_MAP_TYPE_PERF_EVENT_ARRAY = 4
    BPF_MAP_TYPE_PERCPU_HASH = 5
    BPF_MAP_TYPE_PERCPU_ARRAY = 6
    BPF_MAP_TYPE_STACK_TRACE = 7
    BPF_MAP_TYPE_CGROUP_ARRAY = 8
    BPF_MAP_TYPE_LRU_HASH = 9
    BPF_MAP_TYPE_LRU_PERCPU_HASH = 10
    BPF_MAP_TYPE_LPM_TRIE = 11
    BPF_MAP_TYPE_ARRAY_OF_MAPS = 12
    BPF_MAP_TYPE_HASH_OF_MAPS = 13
    BPF_MAP_TYPE_DEVMAP = 14
    BPF_MAP_TYPE_SOCKMAP = 15
    BPF_MAP_TYPE_CPUMAP = 16
    BPF_MAP_TYPE_XSKMAP = 17
    BPF_MAP_TYPE_SOCKHASH = 18
    BPF_MAP_TYPE_CGROUP_STORAGE = 19
    BPF_MAP_TYPE_REUSEPORT_SOCKARRAY = 20
    BPF_MAP_TYPE_PERCPU_CGROUP_STORAGE = 21
    BPF_MAP_TYPE_QUEUE = 22
    BPF_MAP_TYPE_STACK = 23
    BPF_MAP_TYPE_SK_STORAGE = 24
    BPF_MAP_TYPE_DEVMAP_HASH = 25
    BPF_MAP_TYPE_STRUCT_OPS = 26
    BPF_MAP_TYPE_RINGBUF = 27
    BPF_MAP_TYPE_INODE_STORAGE = 28
    BPF_MAP_TYPE_TASK_STORAGE = 29

class KindTypes(IntEnum):
    BTF_KIND_INT = 1            # Integer
    BTF_KIND_PTR = 2            # Pointer
    BTF_KIND_ARRAY = 3          # Array
    BTF_KIND_STRUCT = 4         # Struct
    BTF_KIND_UNION = 5          # Union
    BTF_KIND_ENUM = 6           # Enumeration up to 32-bit values
    BTF_KIND_FWD = 7            # Forward
    BTF_KIND_TYPEDEF = 8        # Typedef
    BTF_KIND_VOLATILE = 9       # Volatile
    BTF_KIND_CONST = 10         # Const
    BTF_KIND_RESTRICT = 11      # Restrict
    BTF_KIND_FUNC = 12          # Function
    BTF_KIND_FUNC_PROTO = 13    # Function Proto
    BTF_KIND_VAR = 14           # Variable
    BTF_KIND_DATASEC = 15       # Section
    BTF_KIND_FLOAT = 16         # Floating point
    BTF_KIND_DECL_TAG = 17      # Decl Tag
    BTF_KIND_TYPE_TAG = 18      # Type Tag
    BTF_KIND_ENUM64 = 19        # Enumeration up to 64-bit values

class BPF_Map:
    def __init__(self, filename: str):
        self.__map_fd = libbpf.bpf_obj_get(os.fsencode(filename))
        if self.__map_fd < 0:
            raise OSError(-self.fd, "failed to access bpf map", filename)

        bpf_map_info = Bpf_map_info()
        rc = libbpf.bpf_obj_get_info_by_fd(self.fd,
                                           ctypes.byref(bpf_map_info),
                                           ctypes.byref(ctypes.c_uint(ctypes.sizeof(bpf_map_info))))
        assert(rc == 0)


        self.map_type = bpf_map_info.type
        self.map_name = bpf_map_info.name
        self.key_size = bpf_map_info.key_size
        self.value_size = bpf_map_info.value_size
        self.max_entries = bpf_map_info.max_entries
        self.map_flags = bpf_map_info.map_flags
        self.key_type = bpf_map_info.btf_key_type_id
        self.value_type = bpf_map_info.btf_value_type_id
        self.__id = bpf_map_info.id

    def __getitem__(self, key):
        """
        LIBBPF_API int bpf_map_lookup_elem(int fd, const void *key, void *value);
        """
        result = None
        if isinstance(key, slice):
            result = []
            for k in range(key.start, key.stop, key.step or 1):
                result.append(self[k])
        else:
            # Assume that if the provided key is not an int is is already a ctypes object
            if isinstance(key, int):
                key = ctypes.c_int(
                    key)# if self.key_type is None else self.key_type(key)
            value = ctypes.c_void_p(
                0)# if self.value_type is None else self.value_type()
            # import pudb; pudb.set_trace()
            err = libbpf.bpf_map_lookup_elem(
                ctypes.c_int(self.__map_fd), ctypes.byref(
                    key), ctypes.byref(value)
            )
            assert err == 0, f"Failed to lookup map elem {key}, {err}"
            if isinstance(value, ctypes.Structure):
                result = value
            else:
                result = value.value

            if result is None:
                result = 0
        return result

    def __setitem__(self, key, value):
        """
        LIBBPF_API int bpf_map_update_elem(int fd, const void *key, const void *value, __u64 flags);
        """
        # there is the option to specify a _as_parameter for custom classes, so they can be used when calling the function

        if isinstance(key, int):
            key = ctypes.c_int(
                key) if self.key_type is None else self.key_type(key)
        if isinstance(value, int):
            value = (
                ctypes.c_int(value)
                if self.value_type is None
                else self.value_type(value)
            )
        err = libbpf.bpf_map_update_elem(
            ctypes.c_int(self.__map_fd),
            ctypes.byref(key),
            ctypes.byref(value),
            ctypes.c_int(0),
        )
        assert err == 0, f"Failed to update map, {err}"

    def __len__(self):
        """Returns the number of max entries"""
        return self.max_entries

    def __iter__(self):
        if self.map_type == MapTypes.BPF_MAP_TYPE_HASH:
            return Bpf_map_iterator(self)
        elif self.map_type == MapTypes.BPF_MAP_TYPE_ARRAY:
            return Bpf_array_iterator(self)

    @property
    def id(self):
        return self.__id

    @property
    def fd(self):
        return self.__map_fd


class Bpf_array_iterator:
    def __init__(self, map: BPF_Map):
        self.__map = map
        self.__index = 0
        if map.map_type != MapTypes.BPF_MAP_TYPE_ARRAY:
            raise Exception("Only array maps are supported")

    def __iter__(self):
        return self

    def __next__(self):
        if self.__index >= len(self.__map):
            raise StopIteration
        else:
            result = self.__map[self.__index]
            self.__index += 1
            return result


class Bpf_map_iterator:
    def __init__(self, map: BPF_Map):
        self.__map = map
        if map.map_type != MapTypes.BPF_MAP_TYPE_HASH:
            raise Exception("Only hash maps are supported")
        # for the first iter we pass 0
        self.last_key = (
            ctypes.c_int(0)
        )
        self.first_iteration = True

    def __iter__(self):
        return self

    def __next__(self):
        # LIBBPF_API int bpf_map_get_next_key(int fd, const void *key, void *next_key);
        # strace og bpftool map dump
        # bpf(BPF_MAP_GET_NEXT_KEY, {map_fd=3, key=NULL, next_key=0x55fd70b6c2c0}, 128) = 0
        # bpf(BPF_MAP_LOOKUP_ELEM, {map_fd=3, key=0x55fd70b6c2c0, value=0x55fd70b6c2e0, flags=BPF_ANY}, 128) = 0
        # bpf(BPF_MAP_GET_NEXT_KEY, {map_fd=3, key=0x55fd70b6c2c0, next_key=0x55fd70b6c2c0}, 128) = 0
        # bpf(BPF_MAP_LOOKUP_ELEM, {map_fd=3, key=0x55fd70b6c2c0, value=0x55fd70b6c2e0, flags=BPF_ANY}, 128) = 0
        if self.first_iteration:
            self.next_exists = (
                libbpf.bpf_map_get_next_key(
                    self.__map.fd, 0, ctypes.byref(self.last_key)
                )
                == 0
            )
            self.first_iteration = False
        else:
            self.next_exists = (
                libbpf.bpf_map_get_next_key(
                    self.__map.fd,
                    ctypes.byref(self.last_key),
                    ctypes.byref(self.last_key),
                )
                == 0
            )
        if not self.next_exists:
            raise StopIteration
        value = self.__map[self.last_key]
        return self.last_key.value, value
