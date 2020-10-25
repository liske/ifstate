from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import ExceptionCollector, NetlinkError
from pprint import pprint


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

    def apply(self, do_apply):
        excpts = ExceptionCollector()

        # get ifindex
        self.idx = next(iter(ipr.link_lookup(ifname=self.iface)), None)

        if self.idx == None:
            logger.warning('link missing', extra={'iface': self.iface})
            return

        changes = []

        # apply qdisc tree
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

        if len(changes) > 0:
            logger.info(
                'change ({})'.format(", ".join(changes)),
                extra={'iface': self.iface, 'style': IfStateLogging.STYLE_CHG})
        else:
            logger.info(
                'ok',
                extra={'iface': self.iface, 'style': IfStateLogging.STYLE_OK})

        return excpts
