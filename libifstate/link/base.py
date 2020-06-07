from libifstate.util import logger, ipr, LogStyle
from libifstate.exception import LinkTypeUnknown
from abc import ABC, abstractmethod

class Link(ABC):
    _nla_prefix = 'IFLA_'
    _classes = {}

    def __new__(cls, *args, **kwargs):
        cname = cls.__name__
        if cname == Link.__name__:
            cname = "{}Link".format(kwargs["kind"].lower().capitalize())

        for c in Link.__subclasses__():
            if c.__name__ == cname:
                return super().__new__(c)

        return super().__new__(GenericLink)
        #raise LinkTypeUnknown()

    def __init__(self, name, **kwargs):
        self.cap_create = True
        self.settings = {
            'ifname': name,
        }
        self.settings.update(kwargs)
        self.attr_map = {
            'kind': ['IFLA_LINKINFO', 'IFLA_INFO_KIND'],
        }
        self.attr_idx = ['link']
        self.idx = None

        if 'address' in self.settings:
            self.idx = next(iter(ipr.link_lookup(
                address=self.settings['address'])), None)
        if self.idx is None:
            self.idx = next(iter(ipr.link_lookup(ifname=name)), None)

    def _drill_attr(self, data, keys):
        key = keys[0]
        d = data.get_attr(key)

        if d is not None:
            if len(keys) > 1:
                return self._drill_attr(d, keys[1:])
            else:
                return d
        else:
            return None

    def get_if_attr(self, key):
        if key == "state":
            return self.iface['state']

        if key in self.attr_map:
            return self._drill_attr(self.iface, self.attr_map[key])

        nla = self.name2nla(key)
        ret = self.iface.get_attr(nla)
        if not ret is None:
            return ret

        info = self.iface.get_attr('IFLA_LINKINFO')
        if not info is None:
            ret = info.get_attr(nla)
            if not ret is None:
                return ret

            info = info.get_attr('IFLA_INFO_DATA')
            if not info is None:
                ret = info.get_attr(nla)
                if not ret is None:
                    return ret

        return None

    def apply(self):
        # lookup for attributes requiring a interface index
        for attr in self.attr_idx:
            if attr in self.settings:
                self.settings[attr] = next(iter(ipr.link_lookup(ifname=self.settings[attr])), self.settings[attr])

        if self.idx is not None:
            self.iface = next(iter(ipr.get_links(self.idx)), None)

            if self.cap_create and self.get_if_attr('kind') != self.settings['kind']:
                self.recreate()
            else:
                self.update()
        else:
            self.create()

    def create(self, oper="add"):
        logger.info(oper, extra={'iface': self.settings['ifname'], 'style': LogStyle.CHG})

        logger.debug("ip link add: {}".format( " ".join("{}={}".format(k, v) for k,v in self.settings.items()) ))
        ipr.link('add', **(self.settings))

    def recreate(self):
        logger.debug('has wrong link kind %s, removing', self.settings['kind'], extra={'iface': self.settings['ifname']})
        ipr.link('del', index=self.idx)
        self.idx = None
        self.create("replace")

    def update(self):
        logger.debug('checking', extra={'iface': self.settings['ifname']})

        old_state = self.iface['state']
        has_changes = False
        for setting in self.settings.keys():
            logger.debug('  %s: %s => %s', setting, self.get_if_attr(
                setting), self.settings[setting], extra={'iface': self.settings['ifname']})
            if setting != 'kind' or self.cap_create:
                has_changes |= self.get_if_attr(setting) != self.settings[setting]

        if has_changes:
            logger.debug('needs to be configured', extra={'iface': self.settings['ifname']})
            if old_state:
                logger.debug('shutting down', extra={'iface': self.settings['ifname']})
                ipr.link('set', index=self.idx, state='down')
                if not 'state' in self.settings:
                    self.settings['state'] = 'up'

            logger.info('change', extra={'iface': self.settings['ifname'], 'style': LogStyle.CHG})
            ipr.link('set', index=self.idx, **(self.settings))
        else:
            logger.info('ok', extra={'iface': self.settings['ifname'], 'style': LogStyle.OK})

    def depends(self):
        return None

    @classmethod
    def name2nla(self, name):
        '''
        Convert human-friendly name into NLA name

        Example: address -> IFLA_ADDRESS

        Requires self.prefix to be set
        '''
        name = name.upper()
        if name.find(self._nla_prefix) == -1:
            name = "%s%s" % (self._nla_prefix, name)
        return name


class GenericLink(Link):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
