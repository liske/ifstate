from pyroute2.netlink.exceptions import NetlinkError


class ExceptionCollector():
    def __init__(self):
        self.excpts = []

    def add(self, op, excpt, **kwargs):
        self.excpts.append({
            'op': op,
            'excpt': excpt,
            'args': kwargs,
        })

    def has_errno(self, errno):
        for e in self.excpts:
            if type(e['excpt']) == NetlinkError and e['excpt'].code == errno:
                return True
        return False

    def get_all(self):
        return self.excpts

class FeatureMissingError(Exception):
    def __init__(self, feature):
        self.feature = feature


class LinkCannotAdd(Exception):
    pass


class LinkTypeUnknown(Exception):
    pass


class LinkDuplicate(Exception):
    pass


class LinkCircularLinked(Exception):
    pass


class LinkNoConfigFound(Exception):
    pass

class ParserValidationError(Exception):
    def __init__(self, detail):
        self.detail = detail

class ParserOSError(Exception):
    def __init__(self, oserr):
        self.fn = oserr.filename
        self.msg = oserr.strerror

class ParserOpenError(ParserOSError):
    pass

class ParserIncludeError(ParserOSError):
    pass

class RouteDupblicate(Exception):
    pass
