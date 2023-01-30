from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import netlinkerror_classes
from libifstate.bpf import libbpf, struct_bpf_prog_info, bpfs_ifstate_dir

from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_SKB_MODE
from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_DRV_MODE
from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_HW_MODE

import ctypes
import os
import shutil

class XDP():
    def __init__(self, iface, xdp):
        self.iface = iface
        self.xdp = xdp

    def apply(self, do_apply, bpf_progs):
        self.link = next(iter(ipr.get_links(ifname=self.iface)), None)

        if self.link == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get ifindex
        self.idx = self.link['index']

        # new BPF instance (from pinned, bpf or xdp settings)
        new_prog_tag = None
        new_prog_fd = None

        # get current BPF tag, if any
        current_prog_tag = None
        current_prog_id = None
        current_attached = None
        ifla_xdp = self.link.get_attr('IFLA_XDP')
        if ifla_xdp is not None:
            current_prog_id = ifla_xdp.get_attr('IFLA_XDP_PROG_ID')
            current_attached = ifla_xdp.get_attr('IFLA_XDP_ATTACHED')

        if current_prog_id:
            current_prog_fd = libbpf.bpf_prog_get_fd_by_id(current_prog_id)
            if current_prog_fd < 0:
                logger.warning('could not get current XDP prog fd for {}: {}'.format(
                    self.iface, os.strerror(-current_prog_fd)))
            else:
                current_prog_info = struct_bpf_prog_info()
                current_prog_size = ctypes.c_uint(ctypes.sizeof(current_prog_info))
                rc = libbpf.bpf_obj_get_info_by_fd(current_prog_fd, ctypes.byref(current_prog_info), ctypes.byref(current_prog_size))
                if rc == 0:
                    current_prog_tag = bytes(current_prog_info.tag).hex()

                    logger.debug('current prog tag: {}'.format(current_prog_tag), extra={
                                'iface': self.iface})
                else:
                    logger.warning('could not get current XDP obj info for {}: {}'.format(
                        self.iface, os.strerror(-rc)))

        logger.debug('current attached: {}'.format(current_attached), extra={
            'iface': self.iface})

        # load new BPF prog
        new_obj = None
        if not self.xdp:
            new_prog_fd = -1
        elif 'pinned' in self.xdp:
            new_prog_fd = libbpf.bpf_obj_get( os.fsencode(self.xdp["pinned"]) )

            if new_prog_fd < 0:
                logger.warning("pinned BPF object '{}' cannot be opened: {}".format(
                    self.xdp["pinned"], os.strerror(-new_prog_fd)))
        elif 'bpf' in self.xdp:
            if bpf_progs is not None:
                (new_prog_fd, new_prog_tag) = bpf_progs.get_bpf(self.xdp["bpf"])

            if new_prog_fd == -1:
                logger.warning("BPF program '{}' not loaded for {}".format(
                    self.xdp["bpf"], self.iface))
            else:
                logger.debug('new prog tag: {}'.format(new_prog_tag), extra={
                            'iface': self.iface})
        else:
            assert False, "unhandled XDP settings"

        # get new prog tag
        if new_prog_fd != -1 and new_prog_tag == None:
            info = struct_bpf_prog_info()
            sz = ctypes.c_uint(ctypes.sizeof(info))
            rc = libbpf.bpf_obj_get_info_by_fd(new_prog_fd, ctypes.byref(info), ctypes.byref(sz))
            if rc == 0:
                new_prog_tag = bytes(info.tag).hex()

                logger.debug('new prog tag: {}'.format(new_prog_tag), extra={
                            'iface': self.iface})
            else:
                logger.warning('XDP failed to get prog info on {}'.format(
                    self.iface))

        # get attach mode flags
        new_attached = self.xdp.get("mode", "auto")
        if type(new_attached) != list:
            new_attached = [new_attached]

        new_flags = 0
        if "auto" in new_attached:
            new_attached = ["xdp", "xdpgeneric", "xdpoffload"]
        else:
            if "xdp" in new_attached:
                new_flags = new_flags | XDP_FLAGS_DRV_MODE
            if "xdpgeneric" in new_attached:
                new_flags = new_flags | XDP_FLAGS_SKB_MODE
            if "xdpoffload" in new_attached:
                new_flags = new_flags | XDP_FLAGS_HW_MODE

        logger.debug('new attached: {}'.format(", ".join(new_attached)), extra={
            'iface': self.iface})

        logger.debug('new flags: {}'.format(new_flags), extra={
            'iface': self.iface})

        # set new XDP prog if tag or attach mode has changed
        if current_prog_tag != new_prog_tag or not current_attached in new_attached:
            if do_apply:
                attach_ok = False
                try:
                    ipr.link('set', index=self.idx, xdp_fd=new_prog_fd, xdp_flags=new_flags)
                    attach_ok = True
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise

                    # try again: detaching XDP first
                    try:
                        ipr.link('set', index=self.idx, xdp_fd=-1)

                        ipr.link('set', index=self.idx, xdp_fd=new_prog_fd, xdp_flags=new_flags)
                        attach_ok = True
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise

                        logger.warning('attaching XDP program on {} failed: {}'.format(
                            self.iface, err.args[1]))

            if new_prog_fd == -1:
                logger.info('detach', extra={
                            'iface': self.iface, 'style': IfStateLogging.STYLE_DEL})
            else:
                logger.info('change', extra={
                            'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
        else:
            logger.info(
                'ok',
                extra={'iface': self.iface, 'style': IfStateLogging.STYLE_OK})

try:
    libbpf.bpf_obj_get_info_by_fd
    libbpf.bpf_object__name
    libbpf.bpf_object__next_program
    libbpf.bpf_object__load
    libbpf.bpf_object__open_file
    libbpf.bpf_object__pin_maps
    libbpf.bpf_prog_get_fd_by_id
    libbpf.bpf_program__fd
    libbpf.bpf_program__section_name
except AttributeError as ex:
    # ignore missing library
    raise ModuleNotFoundError(ex)
