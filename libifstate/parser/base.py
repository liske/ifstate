from libifstate.util import logger
from abc import ABC, abstractmethod


class Parser(ABC):
    _default_ifstates = {
        'ignore': {
            'ipaddr': [
                'fe80::/10'
            ],
            'ipaddr_dynamic': True,
            'ifname': [
                r'^br-[\da-f]{12}',
                r'^docker\d+',
                r'^lo$',
                r'^ppp\d+$',
                r'^veth',
                r'^virbr\d+',
                r'^vrrp\d*\.\d+$'
            ],
            'routes': [
                { 'proto': 1 },
                { 'proto': 2 },
                { 'proto': 8 },
                { 'proto': 9 },
                { 'proto': 10 },
                { 'proto': 11 },
                { 'proto': 12 },
                { 'proto': 13 },
                { 'proto': 14 },
                { 'proto': 15 },
                { 'proto': 16 },
                { 'proto': 42 },
                { 'proto': 186 },
                { 'proto': 187 },
                { 'proto': 188 },
                { 'proto': 189 },
                { 'proto': 192 },
                { 'to': 'ff00::/8' },
            ],
            'rules': [
                { 'proto': 1 },
                { 'proto': 2 },
                { 'proto': 8 },
                { 'proto': 9 },
                { 'proto': 10 },
                { 'proto': 11 },
                { 'proto': 12 },
                { 'proto': 13 },
                { 'proto': 14 },
                { 'proto': 15 },
                { 'proto': 16 },
                { 'proto': 42 },
                { 'proto': 186 },
                { 'proto': 187 },
                { 'proto': 188 },
                { 'proto': 189 },
                { 'proto': 192 },
            ],
        },
        'interfaces': {}
    }

    @abstractmethod
    def __init__(self, name, **kwargs):
        self.ifstate = {}
        pass

    def merge(self, a, b):
        if not b is None:
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
