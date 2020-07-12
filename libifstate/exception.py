from pyroute2.netlink.exceptions import NetlinkError

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

class RouteDupblicate(Exception):
    pass
