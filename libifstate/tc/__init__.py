from libifstate.util import logger, IfStateLogging
from libifstate.exception import ExceptionCollector, netlinkerror_classes

import errno
from pyroute2 import NetlinkError

class TC():
    ROOT_HANDLE = 0xFFFFFFFF
    INGRESS_HANDLE = 0xFFFF0000
    INGRESS_PARENT = 0xFFFFFFF1
    HMASK_MAJOR = 0xFFFF0000
    HMASK_MINOR = 0x0000FFFF

    def int2handle(h):
        maj = "{:x}".format((h & TC.HMASK_MAJOR) >> 16)
        mi = (h & TC.HMASK_MINOR)

        if mi == 0:
            mi = ""
        else:
            mi = "{:x}".format(mi)

        return ":".join((maj, mi))

    def handle2int(s):
        if isinstance(s, int):
            return s

        if s == "root":
            return TC.ROOT_HANDLE

        l = s.split(':')
        if l[1] == "":
            l[1] = "0"

        return int(l[0], 16) << 16 | int(l[1], 16)

    def __init__(self, netns, iface, tc):
        self.netns = netns
        self.iface = iface
        self.idx = None
        self.tc = tc

    def get_qdisc(self, netns_qdiscs, parent):
        for qdisc in netns_qdiscs:
            if qdisc['parent'] == parent:
                return qdisc

    def get_qchild(self, netns_qdiscs, parent, slot):
        for qdisc in netns_qdiscs:
            if qdisc['parent'] == parent | slot:
                return qdisc

    def apply_ingress(self, ingress, qdisc, excpts, do_apply):
        logger.debug('checking ingress qdisc', extra={'iface': self.iface})
        if not ingress:
            if qdisc:
                if do_apply:
                    opts = {
                        "index": self.idx,
                        "parent": TC.INGRESS_PARENT,
                    }
                    try:
                        self.netns.ipr.tc("del", **opts)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('removing ingress qdisc on {} failed: {}'.format(
                            self.iface, err.args[1]))
                        excpts.add('del', err, **opts)
                return True
        else:
            if not qdisc:
                if do_apply:
                    opts = {
                        "index": self.idx,
                        "kind": "ingress",
                    }
                    try:
                        self.netns.ipr.tc("add", **opts)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('adding ingress qdisc on {} failed: {}'.format(
                            self.iface, err.args[1]))
                        excpts.add('add', err, **opts)
                return True

        return False

    def apply_qtree(self, tc, qdisc, ipr_qdiscs, parent, excpts, do_apply, recreate=False):
        # if tc is None, we shall cleanup the qdisc tree
        # (remove the root qdisc to restore the interface's default)
        if tc is None:
            if do_apply:
                try:
                    self.netns.ipr.tc("del", index=self.idx, parent=parent)
                    return True
                except NetlinkError as ex:
                    # the native qdisc cannot be removed but only replaced,
                    # so we ignore any ENOENT
                    if ex.code != errno.ENOENT:
                        logger.exception('cannot remove qdisc')
            return False

        if qdisc is None:
            recreate = True

        if not recreate:
            logger.debug('  kind: {} => {}'.format(
                qdisc.get_attr("TCA_KIND"), tc["kind"]), extra={'iface': self.iface})
            if tc["kind"] != qdisc.get_attr("TCA_KIND"):
                recreate = True
            else:
                logger.debug('  handle: {} => {}'.format(
                    TC.int2handle(qdisc["handle"]), tc["handle"]), extra={'iface': self.iface})
                if TC.handle2int(tc["handle"]) != qdisc["handle"]:
                    recreate = True

        if recreate and do_apply:
            if qdisc is not None:
                try:
                    self.netns.ipr.tc("del", index=self.idx, parent=qdisc["parent"])
                except NetlinkError as ex:
                    # the native qdisc cannot be removed but only replaced,
                    # so we ignore any ENOENT
                    if ex.code != errno.ENOENT:
                        logger.exception('cannot remove qdisc')

        opts = {
            "index": self.idx,
            "parent": TC.int2handle(parent),
        }
        for k, v in tc.items():
            if k != "children":
                opts[k] = v

        if do_apply:
            if recreate:
                try:
                    self.netns.ipr.tc("add", **opts)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('adding qdisc {} on {} failed: {}'.format(
                        opts.get("handle"), self.iface, err.args[1]))
                    excpts.add('add', err, **opts)
            else:
                # soft update for TCA_OPTIONS
                try:
                    self.netns.ipr.tc("change", **opts)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    logger.warning('updating qdisc {} on {} failed: {}'.format(
                        opts.get("handle"), self.iface, err.args[1]))
                    excpts.add('change', err, **opts)

        changes = recreate
        if "children" in tc:
            for i in range(len(tc["children"])):
                changes = changes or self.apply_qtree(tc["children"][i], self.get_qchild(
                    ipr_qdiscs, qdisc["handle"], i+1), ipr_qdiscs, TC.handle2int(tc["handle"]) | i + 1, do_apply, recreate)

        return changes

    def apply_filter(self, tc, ipr_filters, excpts, do_apply):
        tc_filters = {}
        # assign prio numbers if missing
        for i in range(len(tc)):
            if not "prio" in tc[i]:
                tc[i]["prio"] = 0xc001 - len(tc) + i

            parent = TC.handle2int(tc[i].get("parent", 0))
            if not parent in tc_filters:
                tc_filters[parent] = {}

            tc_filters[parent][tc[i]["prio"]] = tc[i]

        changes = False
        # remove unreferenced filters
        removed = {}
        for ipr_filter in ipr_filters:
            prio = ipr_filter["info"] >> 16

            parent = TC.handle2int(ipr_filter.get("parent", 0))
            rm = not parent in tc_filters
            rm |= parent in tc_filters and \
                prio not in tc_filters[parent]
            if rm and prio not in removed.get(parent, []):
                changes = True
                if not parent in removed:
                    removed[parent] = []
                removed[parent].append(prio)
                if do_apply:
                    opts = {
                        "index": self.idx,
                        "info": ipr_filter["info"],
                        "parent": parent,
                    }
                    try:
                        self.netns.ipr.del_filter_by_info(**opts)
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('deleting filter #{} on {} failed: {}'.format(
                            prio, self.iface, err.args[1]))
                        excpts.add('del', err, **opts)

        if do_apply:
            for parent in tc_filters.keys():
                for tc_filter in tc_filters[parent].values():
                    tc_filter['index'] = self.idx
                    if "action" in tc_filter:
                        for action in tc_filter["action"]:
                            if action["kind"] == "mirred":
                                # get ifindex
                                action["ifindex"] = next(
                                    iter(self.netns.ipr.link_lookup(ifname=action["dev"])), None)

                                if self.idx == None:
                                    logger.warning("filter #{} references unknown interface {}".format(
                                        tc_filter["prio"], action["dev"]), extra={'iface': self.iface})
                                    continue
                    if "parent" in tc_filter:
                        tc_filter["parent"] = TC.handle2int(tc_filter["parent"])
                    try:
                        try:
                            self.netns.ipr.tc("replace-filter", **tc_filter)
                            # replace seems only to work if there is no filter
                            # => something has changed
                            changes = True
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            # replace does not work, supress changes result
                            # for now
                            #changes = True
                            opts = {
                                "index": self.idx,
                                "info": tc_filter["prio"] << 16,
                                "parent": parent,
                            }
                            self.netns.ipr.del_filter_by_info(**opts)
                            self.netns.ipr.tc("add-filter", **tc_filter)

                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        logger.warning('replace filter #{} on {} failed: {}'.format(
                            tc_filter['prio'], self.iface, err.args[1]))
                        excpts.add('replace', err, **tc_filter)

        return changes

    def apply(self, do_apply):
        excpts = ExceptionCollector(ifname=self.iface)

        # get ifindex
        self.idx = next(iter(self.netns.ipr.link_lookup(ifname=self.iface)), None)

        if self.idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        changes = []
        ipr_qdiscs = None

        # apply ingress qdics
        if "ingress" in self.tc:
            ipr_qdiscs = self.netns.ipr.get_qdiscs(index=self.idx)
            if self.apply_ingress(self.tc["ingress"],
                                  self.get_qdisc(
                                      ipr_qdiscs, TC.INGRESS_PARENT),
                                  excpts,
                                  do_apply):
                changes.append("ingress")

        # apply qdisc tree
        if "qdisc" in self.tc:
            if ipr_qdiscs is None:
                ipr_qdiscs = self.netns.ipr.get_qdiscs(index=self.idx)
            logger.debug('checking qdisc tree', extra={'iface': self.iface})
            if self.apply_qtree(
                    self.tc["qdisc"],
                    self.get_qdisc(ipr_qdiscs, TC.ROOT_HANDLE),
                    ipr_qdiscs,
                    TC.ROOT_HANDLE,
                    excpts,
                    do_apply):
                changes.append("qdisc")

        # apply filters
        if "filter" in self.tc:
            ipr_filters = self.netns.ipr.get_filters(
                index=self.idx) + self.netns.ipr.get_filters(index=self.idx, parent=TC.INGRESS_HANDLE)
            logger.debug('checking filters', extra={'iface': self.iface})
            if self.apply_filter(
                    self.tc["filter"],
                    ipr_filters,
                    excpts,
                    do_apply):
                changes.append("filter")

        if len(changes) > 0:
            logger.log_change('tc', 'change ({})'.format(", ".join(changes)))
        else:
            logger.log_ok('tc')

        return excpts
