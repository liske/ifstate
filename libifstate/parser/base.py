from libifstate.util import logger
from abc import ABC, abstractmethod

class IfAttrList(list):
    def __init__(self, l):
        for i, v in enumerate(l):
            if isinstance(v, dict):
                l[i] = IfAttrDict(v)
            elif isinstance(v, list):
                l[i] = IfAttrList(v)
        super().__init__(l)

class IfAttrDict(dict):
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, dict):
                d[k] = IfAttrDict(v)
            elif isinstance(v, list):
                d[k] = IfAttrList(v)
        super().__init__(d)

    def __getitem__(self, key):
        # if not key in self:
        #     print("booom")
        return super().__getitem__(key)

class Parser(ABC):
    _default_ifstates = {
        'ignore': [
            r'^docker\d+',
            r'^lo$',
            r'^ppp\d+$',
            r'^veth',
            r'^virbr\d+',
        ],
        'interfaces': {}
    }

    @abstractmethod
    def __init__(self, name, **kwargs):
        self.ifstate = {}
        pass

    def config(self):
        return IfAttrDict({**self._default_ifstates, **self.ifstates})
