from libifstate.util import logger, ipr
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

        raise LinkTypeUnknown()

    def __init__(self, name, **kwargs):
        self.cap_create = True
        self.settings = {
            'ifname': name,
        }
        self.settings.update(kwargs)
        self.attr_map = {
            'kind': ['IFLA_LINKINFO', 'IFLA_INFO_KIND'],
        }
        self.attr_idx = []
        self.idx = None

        if 'address' in self.settings:
            self.idx = next(iter(ipr.link_lookup(
                address=self.settings['address'])), None)
        if self.idx is None:
            self.idx = next(iter(ipr.link_lookup(ifname=name)), None)

        logger.debug('%s init %s', self.settings['ifname'], self.settings)

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
        if key in self.attr_map:
            return self._drill_attr(self.iface, self.attr_map[key])

        return self.iface.get_attr(self.name2nla(key))

    def commit(self):
        logger.debug('%s starting commit', self.settings['ifname'])

        # lookup for attributes requiring a interface index
        for attr in self.attr_idx:
            self.settings[attr] = next(iter(ipr.link_lookup(ifname=self.settings[attr])), self.settings[attr])

        if self.idx is not None:
            self.iface = next(iter(ipr.get_links(self.idx)), None)

            if self.cap_create and self.get_if_attr('kind') != self.settings['kind']:
                self.recreate()
            else:
                self.update()
        else:
            self.create()
        logger.debug('%s finished commit', self.settings['ifname'])

    def create(self):
        logger.debug('%s creating link', self.settings['ifname'])

        ipr.link('add', **(self.settings))

    def recreate(self):
        logger.debug('%s recreating link', self.settings['ifname'])
        ipr.link('del', index=self.idx)
        self.idx = None
        self.create()

    def update(self):
        logger.debug('%s updating link', self.settings['ifname'])

        old_state = self.iface['state']
        has_changes = False
        for setting in self.settings.keys():
            logger.debug('%s  %s: %s => %s', self.settings['ifname'], setting, self.get_if_attr(
                setting), self.settings[setting])
            if setting != 'kind' or self.cap_create:
                has_changes |= self.get_if_attr(
                    setting) != self.settings[setting]

        if has_changes:
            logger.debug('%s pending changes', self.settings['ifname'])
            if old_state:
                logger.debug('%s set state to down', self.settings['ifname'])
                ipr.link('set', index=self.idx, state='down')
                if not 'state' in self.settings:
                    self.settings['state'] = 'up'

            logger.debug('%s updating settings', self.settings['ifname'])
            ipr.link('set', index=self.idx, **(self.settings))
        else:
            logger.debug('%s no pending changes', self.settings['ifname'])

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
