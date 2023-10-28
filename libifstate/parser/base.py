from libifstate.util import logger
from libifstate.exception import ParserValidationError
from abc import ABC, abstractmethod
from copy import deepcopy


class Parser(ABC):
    _default_lo_link = {
        'name': 'lo',
        'addresses': [
            '127.0.0.1/8',
            '::1/128',
        ],
        'link': {
            'kind': 'physical',
            'state': 'up',
            'mtu': 65536,
        }
    }
    _default_ifstates = {
        'ignore': {
            'ipaddr_builtin': [
                'fe80::/10'
            ],
            'ipaddr_dynamic': True,
            'ifname_builtin': [
                r'^br-[\da-f]{12}',
                r'^docker\d+',
                r'^ppp\d+$',
                r'^veth',
                r'^virbr\d+',
                r'^vrrp\d*\.\d+$'
            ],
            'fdb_builtin': [
                r'^33:33:',
                r'^01:00:5e:'
            ],
            'routes_builtin': [
                {'proto': 1},
                {'proto': 2},
                {'proto': 8},
                {'proto': 9},
                {'proto': 10},
                {'proto': 11},
                {'proto': 12},
                {'proto': 13},
                {'proto': 14},
                {'proto': 15},
                {'proto': 16},
                {'proto': 18},
                {'proto': 42},
                {'proto': 186},
                {'proto': 187},
                {'proto': 188},
                {'proto': 189},
                {'proto': 192},
                {'to': 'ff00::/8'},
            ],
            'rules_builtin': [
                {'proto': 1},
                {'proto': 2},
                {'proto': 8},
                {'proto': 9},
                {'proto': 10},
                {'proto': 11},
                {'proto': 12},
                {'proto': 13},
                {'proto': 14},
                {'proto': 15},
                {'proto': 16},
                {'proto': 18},
                {'proto': 42},
                {'proto': 186},
                {'proto': 187},
                {'proto': 188},
                {'proto': 189},
                {'proto': 192},
            ],
        },
        'cshaper': {
            'default': {
                'egress_qdisc': {
                    'kind': 'cake',
                    'handle': '1:',
                },
                'ingress_qdisc': {
                    'kind': 'cake',
                    'handle': '1:',
                },
                'ingress_ifname': {
                    'search': r'^\D{1,3}',
                    'replace': 'ifb',
                }
            }
        }
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

    def _update_lo(self, cfg):
        if 'interfaces' in cfg:
            lo = next((idx for idx, iface in enumerate(cfg['interfaces']) if iface['name'] == 'lo'), None)
            if lo is not None:
                cfg['interfaces'][lo] = self.merge(deepcopy(Parser._default_lo_link), cfg['interfaces'][lo])
            else:
                cfg['interfaces'].append(Parser._default_lo_link)

    def config(self):
        # merge builtin defaults with config
        cfg = (self.merge(deepcopy(Parser._default_ifstates), self.ifstates))

        # 'ignore' should still be an object
        try:
            iter(cfg["ignore"])
        except TypeError:
            raise ParserValidationError("$.ignore: is not of type 'object'")

        # add loopback interface defaults
        self._update_lo(cfg)
        for namespace in cfg.get('namespaces', {}):
            self._update_lo(cfg['namespaces'][namespace])

        # merge builtin defaults
        for k in list(cfg["ignore"]):
            if k.endswith("_builtin"):
                n = k[:-8]
                if n in cfg["ignore"]:
                    try:
                        cfg["ignore"][n] += cfg["ignore"][k]
                    except TypeError:
                        raise ParserValidationError("$.ignore.{}: is not of type '{}'".format(
                            n, type(cfg["ignore"][k]).__name__))
                else:
                    cfg["ignore"][n] = cfg["ignore"][k]
                del(cfg["ignore"][k])

        return cfg
