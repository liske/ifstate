from libifstate.util import logger
from abc import ABC, abstractmethod


class Parser(ABC):
    _default_ifstates = {
        'ignore': {
            'ipaddr': [
                'fe80::/10',
                'ff00::/8',
            ],
            'ifname': [
                r'^docker\d+',
                r'^lo$',
                r'^ppp\d+$',
                r'^veth',
                r'^virbr\d+',
                r'^br-[\da-f]{12}',
            ],
            'routes': {
                'protos': [1, 2, 8, 9, 10, 11, 12, 13, 14, 15, 16, 42, 186, 187, 188, 189, 192],
            },
            'rules': {
                'protos': [1, 2, 8, 9, 10, 11, 12, 13, 14, 15, 16, 42, 186, 187, 188, 189, 192],
            },
        },
        'interfaces': {}
    }

    @abstractmethod
    def __init__(self, name, **kwargs):
        self.ifstate = {}
        pass

    def merge(self, a, b):
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key])
                else:
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    def config(self):
        return (self.merge(self._default_ifstates, self.ifstates))
