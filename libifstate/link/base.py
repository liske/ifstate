from libifstate.util import logger, ipr, LogStyle
from libifstate.exception import LinkTypeUnknown, NetlinkError
from abc import ABC, abstractmethod
import os
import subprocess
import yaml


class Link(ABC):
    _nla_prefix = 'IFLA_'
    _classes = {}

    def __new__(cls, *args, **kwargs):
        cname = cls.__name__
        if cname == Link.__name__:
            cname = "{}Link".format(args[1]['kind'].lower().capitalize())

        for c in Link.__subclasses__():
            if c.__name__ == cname:
                return super().__new__(c)

        return super().__new__(GenericLink)
        #raise LinkTypeUnknown()

    def __init__(self, name, link, ethtool):
        self.cap_create = True
        self.cap_ethtool = False
        self.settings = {
            'ifname': name,
        }
        self.settings.update(link)
        self.ethtool = None
        self.attr_map = {
            'kind': ['IFLA_LINKINFO', 'IFLA_INFO_KIND'],
        }
        self.attr_idx = ['link', 'master', 'gre_link',
                         'ip6gre_link', 'vxlan_link', 'xfrm_link']
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

    def get_ethtool_fn(self, setting):
        return "/run/ifstate-ethtool:{}_{}.state".format(self.idx, setting)

    def get_ethtool_state(self, settings):
        ethtool = {}

        for setting in settings:
            ethtool[setting] = {}
            fn = self.get_ethtool_fn(setting)

            if not os.path.isfile(fn):
                logger.debug('no prior ethtool %s state available', setting,
                             extra={'iface': self.settings['ifname']})
                continue

            # try:
            with open(fn) as fh:
                ethtool[setting] = yaml.load(fh, Loader=yaml.SafeLoader)
            # except Exception as err:
            #     logger.warning('parsing {} failed: {}'.format(
            #         fn, err.args[1]))

        return ethtool

    def set_ethtool_state(self, ifname):
        logger.info(
            'change (ethtool)', extra={'iface': self.settings['ifname'], 'style': LogStyle.CHG})
        for setting, options in self.ethtool.items():
            cmd = ["ethtool"]
            if setting in ['coalesce', 'features', 'pause']:
                cmd.append("--{}".format(setting))
            elif setting in ['nfc']:
                cmd.append("--config-{}".format(setting))
            else:
                cmd.append("--set-{}".format(setting))
            cmd.append(ifname)
            for option, value in options.items():
                if type(value) == bool:
                    value = {True: "on", False: "off"}[value]
                value = str(value)
                cmd.extend([option, value])
            logger.debug("{}".format(" ".join(cmd)))
            try:
                res = subprocess.run(cmd)
                if res.returncode != 0:
                    logger.warning(
                        '`{}` has failed'.format(" ".join(cmd[0:3])))
                    return
            except Exception as err:
                logger.warning('failed to run `{}`: {}'.format(
                    " ".join(cmd[0:3]), err.args[1]))
                return

            fn = self.get_ethtool_fn(setting)
            with open(fn, 'w') as fh:
                yaml.dump(options, fh)

    def apply(self, do_apply):
        # lookup for attributes requiring a interface index
        for attr in self.attr_idx:
            if attr in self.settings:
                self.settings[attr] = next(iter(ipr.link_lookup(
                    ifname=self.settings[attr])), self.settings[attr])

        if self.idx is not None:
            self.iface = next(iter(ipr.get_links(self.idx)), None)

            # check for ifname collisions
            idx = next(iter(ipr.link_lookup(
                ifname=self.settings['ifname'])), None)
            if idx is not None and idx != self.idx and do_apply:
                try:
                    ipr.link('set', index=idx, state='down')
                    ipr.link('set', index=idx, ifname='{}!'.format(
                        self.settings['ifname']))
                except NetlinkError as err:
                    logger.warning('renaming link {} failed: {}'.format(
                        self.settings['ifname'], err.args[1]))

            if self.cap_create and self.get_if_attr('kind') != self.settings['kind']:
                self.recreate(do_apply)
            else:
                self.update(do_apply)
        else:
            self.create(do_apply)

    def create(self, do_apply, oper="add"):
        logger.info(
            oper, extra={'iface': self.settings['ifname'], 'style': LogStyle.CHG})

        logger.debug("ip link add: {}".format(
            " ".join("{}={}".format(k, v) for k, v in self.settings.items())))
        if do_apply:
            try:
                ipr.link('add', **(self.settings))
            except NetlinkError as err:
                logger.warning('adding link {} failed: {}'.format(
                    self.settings['ifname'], err.args[1]))

        if not self.ethtool is None:
            logger.debug("ethtool: {}".format(self.ethtool))
            if do_apply:
                self.set_ethtool_state()

    def recreate(self, do_apply):
        logger.debug('has wrong link kind %s, removing', self.settings['kind'], extra={
                     'iface': self.settings['ifname']})
        if do_apply:
            try:
                ipr.link('del', index=self.idx)
            except NetlinkError as err:
                logger.warning('removing link {} failed: {}'.format(
                    self.settings['ifname'], err.args[1]))
        self.idx = None
        self.create(do_apply, "replace")

    def update(self, do_apply):
        logger.debug('checking', extra={'iface': self.settings['ifname']})

        old_state = self.iface['state']
        has_link_changes = False
        for setting in self.settings.keys():
            logger.debug('  %s: %s => %s', setting, self.get_if_attr(
                setting), self.settings[setting], extra={'iface': self.settings['ifname']})
            if setting != 'kind' or self.cap_create:
                has_link_changes |= self.get_if_attr(
                    setting) != self.settings[setting]

        has_ethtool_changes = False
        if not self.ethtool is None:
            ethtool = self.get_ethtool_state(self.ethtool.keys())
            if ethtool is None:
                has_ethtool_changes = self.ethtool
            else:
                for setting, options in self.ethtool.items():
                    if not setting in ethtool:
                        has_ethtool_changes |= True
                    else:
                        for option in options.keys():
                            logger.debug('  %s.%s: %s => %s', setting, option, ethtool[setting].get(option), self.ethtool[setting][option], extra={'iface': self.settings['ifname']})
                            has_ethtool_changes |= self.ethtool[setting][option] != ethtool[setting].get(
                                option)

        if has_link_changes:
            logger.debug('needs to be configured', extra={
                         'iface': self.settings['ifname']})
            if old_state:
                logger.debug('shutting down', extra={
                             'iface': self.settings['ifname']})
                if do_apply:
                    try:
                        ipr.link('set', index=self.idx, state='down')
                    except NetlinkError as err:
                        logger.warning('shutting down link {} failed: {}'.format(
                            self.settings['ifname'], err.args[1]))
                if not 'state' in self.settings:
                    self.settings['state'] = 'up'

            if has_ethtool_changes:
                self.set_ethtool_state(self.get_if_attr('ifname'))

            if self.get_if_attr('ifname') == self.settings['ifname']:
                logger.info('change', extra={
                            'iface': self.settings['ifname'], 'style': LogStyle.CHG})
            else:
                logger.info('change (was {})'.format(self.get_if_attr('ifname')), extra={
                            'iface': self.settings['ifname'], 'style': LogStyle.CHG})
            if do_apply:
                try:
                    ipr.link('set', index=self.idx, **(self.settings))
                except NetlinkError as err:
                    logger.warning('updating link {} failed: {}'.format(
                        self.settings['ifname'], err.args[1]))
        else:
            if has_ethtool_changes:
                self.set_ethtool_state(self.get_if_attr('ifname'))
            logger.info(
                'ok', extra={'iface': self.settings['ifname'], 'style': LogStyle.OK})

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
    def __init__(self, name, link, ethtool):
        super().__init__(name, link, ethtool)
