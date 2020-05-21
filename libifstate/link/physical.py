from libifstate.link.base import Link
from libifstate.exception import LinkCannotAdd

class PhysicalLink(Link):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.cap_create = False

    def create(self):
        raise LinkCannotAdd()
