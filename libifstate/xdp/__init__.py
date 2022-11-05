from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import netlinkerror_classes
from libifstate.bpf import libbpf, struct_bpf_prog_info

from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_SKB_MODE
from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_DRV_MODE
from pyroute2.netlink.rtnl.ifinfmsg import XDP_FLAGS_HW_MODE

import ctypes
import os

class XDP():
    def __init__(self, iface, xdp):
        self.iface = iface
        self.xdp = xdp

    def apply(self, do_apply):
        self.link = next(iter(ipr.get_links(ifname=self.iface)), None)

        if self.link == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        # get ifindex
        self.idx = self.link['index']

        # get current BPF tag, if any
        current_prog_tag = None
        current_prog_id = self.link.get_attr('IFLA_XDP', {}).get('IFLA_XDP_PROG_ID')
        current_attached = self.link.get_attr('IFLA_XDP', {}).get('IFLA_XDP_ATTACHED')
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
        new_prog_tag = None
        new_prog_fd = None
        if not self.xdp:
            new_prog_fd = -1
        elif 'pinned' in self.xdp:
            fh = open(self.xdp["pinned"], 'r')
            new_prog_fd = fh.fileno()
        elif 'object' in self.xdp:
            obj = libbpf.bpf_object__open_file(
                os.fsencode(self.xdp["object"]),
                None,
            )
            if not obj:
                logger.warning('XDP open on {} failed: {}'.format(
                    self.iface, os.strerror(-current_prog_fd)))
                return

            logger.debug('loaded object: {}'.format(libbpf.bpf_object__name(obj).decode('ascii')), extra={
                        'iface': self.iface})

            rc = libbpf.bpf_object__load(obj)
            if rc < 0:
                logger.warning('XDP load on {} failed: {}'.format(
                    self.iface, os.strerror(-rc)))
                return

            prog = libbpf.bpf_object__next_program(obj, None)
            while prog:
                section = libbpf.bpf_program__section_name(prog).decode('ascii')

                logger.debug('  section: {}'.format(section), extra={
                            'iface': self.iface})

                if section == self.xdp.get('section', 'xdp'):
                    break
                prog = libbpf.bpf_object__next_program(obj, prog)

            if not prog:
                logger.warning('XDP section {} on {} not found'.format(
                    self.xdp.get('section'), self.iface))
                return

            # get prog fd
            new_prog_fd = libbpf.bpf_program__fd(prog)
            if not new_prog_fd:
                logger.warning('XDP failed to get prog fd on {}'.format(
                    self.iface))
                return
        else:
            assert False, "unhandled XDP settings"

        # get new prog tag
        if new_prog_fd != -1:
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
                try:
                    ipr.link('set', index=self.idx, xdp_fd=new_prog_fd, xdp_flags=new_flags)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise

                    if new_prog_fd == -1:
                        logger.warning('attaching XDP program on {} failed: {}'.format(
                            self.iface, err.args[1]))
                    else:
                        # try again: detaching XDP first
                        try:
                            ipr.link('set', index=self.idx, xdp_fd=-1)

                            ipr.link('set', index=self.idx, xdp_fd=new_prog_fd, xdp_flags=new_flags)
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
    libbpf.bpf_prog_get_fd_by_id
    libbpf.bpf_program__fd
    libbpf.bpf_program__section_name
except AttributeError as ex:
    # ignore missing library
    raise ModuleNotFoundError(ex)
