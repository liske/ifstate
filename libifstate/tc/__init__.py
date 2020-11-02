from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import ExceptionCollector, NetlinkError


class TC():
    ROOT_HANDLE = 0xFFFFFFFF
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
        if s == "root":
            return TC.ROOT_HANDLE

        l = s.split(':')
        if l[1] == "":
            l[1] = "0"

        return int(l[0]) << 16 | int(l[1])

    def __init__(self, iface, tc):
        self.iface = iface
        self.idx = None
        self.tc = tc

    def get_qroot(self, ipr_qdiscs):
        for qdisc in ipr_qdiscs:
            if qdisc['parent'] == TC.ROOT_HANDLE:
                return qdisc

    def get_qchild(self, ipr_qdiscs, parent, slot):
        for qdisc in ipr_qdiscs:
            if qdisc['parent'] == parent | slot:
                return qdisc

    def apply_qtree(self, tc, qdisc, ipr_qdiscs, parent, excpts, do_apply, recreate=False):
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
                    ipr.tc("del", index=self.idx, parent=qdisc["parent"])
                except:
                    pass

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
                    ipr.tc("add", **opts)
                except NetlinkError as err:
                    logger.warning('adding qdisc {} on {} failed: {}'.format(
                        opts.get("handle"), self.iface, err.args[1]))
                    excpts.add('add', err, **opts)
            else:
                # soft update for TCA_OPTIONS
                try:
                    ipr.tc("change", **opts)
                except NetlinkError as err:
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
            tc[i]["prio"] = 0xc001 - len(tc) + i
            tc_filters[tc[i]["prio"]] = tc[i]

        changes = False
        # remove unreferenced filters
        removed = []
        for ipr_filter in ipr_filters:
            prio = ipr_filter["info"] >> 16

            if prio not in tc_filters and prio not in removed:
                changes = True
                removed.append(prio)
                if do_apply:
                    opts = {
                        "index": self.idx,
                        "info": ipr_filter["info"],
                    }
                    try:
                        ipr.del_filter_by_info(**opts)
                    except NetlinkError as err:
                        logger.warning('deleting filter #{} on {} failed: {}'.format(
                            prio, self.iface, err.args[1]))
                        excpts.add('del', err, **opts)

        if do_apply:
            for tc_filter in tc_filters.values():
                tc_filter['index'] = self.idx
                if "action" in tc_filter:
                    for action in tc_filter["action"]:
                        if action["kind"] == "mirred":
                            # get ifindex
                            action["ifindex"] = next(
                                iter(ipr.link_lookup(ifname=action["dev"])), None)

                            if self.idx == None:
                                logger.warning("filter #{} references unknown interface {}".format(
                                    tc_filter["prio"], action["dev"]), extra={'iface': self.iface})
                                continue
                try:
                    try:
                        ipr.tc("replace-filter", **tc_filter)
                    except NetlinkError as err:
                        # something failed... try again
                        # after removing the filter
                        changes = True
                        ipr.del_filter_by_info(
                            index=self.idx, info=tc_filter["prio"] << 16)
                        ipr.tc("add-filter", **tc_filter)

                except NetlinkError as err:
                    logger.warning('replace filter #{} on {} failed: {}'.format(
                        tc_filter['prio'], self.iface, err.args[1]))
                    excpts.add('replace', err, **tc_filter)
        return changes

    def apply(self, do_apply):
        excpts = ExceptionCollector()

        # get ifindex
        self.idx = next(iter(ipr.link_lookup(ifname=self.iface)), None)

        if self.idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        changes = []

        # apply qdisc tree
        if "qdisc" in self.tc:
            ipr_qdiscs = ipr.get_qdiscs(index=self.idx)
            logger.debug('checking qdisc tree', extra={'iface': self.iface})
            if self.apply_qtree(
                    self.tc["qdisc"],
                    self.get_qroot(ipr_qdiscs),
                    ipr_qdiscs,
                    TC.ROOT_HANDLE,
                    excpts,
                    do_apply):
                changes.append("qdisc")

        # apply filters
        if "filter" in self.tc:
            ipr_filters = ipr.get_filters(index=self.idx)
            logger.debug('checking filters', extra={'iface': self.iface})
            if self.apply_filter(
                    self.tc["filter"],
                    ipr_filters,
                    excpts,
                    do_apply):
                changes.append("filter")

        if len(changes) > 0:
            logger.info(
                'change ({})'.format(", ".join(changes)),
                extra={'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
        else:
            logger.info(
                'ok',
                extra={'iface': self.iface, 'style': IfStateLogging.STYLE_OK})

        return excpts
