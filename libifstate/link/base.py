from libifstate.util import logger, ipr, IfStateLogging
from libifstate.exception import ExceptionCollector, LinkTypeUnknown, netlinkerror_classes
from libifstate.brport import BRPort
from libifstate.routing import RTLookups
from abc import ABC, abstractmethod
import os
import subprocess
import yaml
import shutil
import copy

ethtool_path = shutil.which("ethtool") or '/usr/sbin/ethtool'


class Link(ABC):
    _nla_prefix = 'IFLA_'
    _classes = {}
    attr_value_maps = {
        # === bond ===
        'bond_mode': {
            0: 'balance-rr',
            1: 'active-backup',
            2: 'balance-xor',
            3: 'broadcast',
            4: '802.3ad',
            5: 'balance-tlb',
            6: 'balance-alb',
        },
        'bond_arp_validate': {
            0: "none",
            1: "active",
            2: "backup",
            3: "all",
            4: "filter",
            5: "filter_active",
            6: "filter_backup"
        },
        'bond_arp_all_targets': {
            0: "any",
            1: "all",
        },
        'bond_primary_reselect': {
            0: "always",
            1: "better",
            2: "failure",
        },
        'bond_fail_over_mac': {
            0: "none",
            1: "active",
            2: "follow",
        },
        'bond_xmit_hash_policy': {
            0: 'layer2',
            1: 'layer3+4',
            2: 'layer2+3',
            3: 'encap2+3',
            4: 'encap3+4',
            5: 'vlan+srcmac',
        },
        'bond_ad_lacp_rate': {
            0: 'slow',
            1: 'fast',
        },
        'bond_ad_select': {
            0: "stable",
            1: "bandwidth",
            2: "count",
        },
        # === vlan ===
        'vlan_protocol': {
            0x88a8: '802.1ad',
            0x8100: '802.1q',
        },
    }
    attr_value_lookup = {
        'group': RTLookups.group,
    }

    def __new__(cls, *args, **kwargs):
        cname = cls.__name__
        if cname == Link.__name__:
            cname = "{}Link".format(args[1]['kind'].lower().capitalize())

        for c in Link.__subclasses__():
            if c.__name__ == cname:
                return super().__new__(c)

        return super().__new__(GenericLink)
        #raise LinkTypeUnknown()

    def __init__(self, name, link, ethtool, vrrp, brport):
        self.cap_create = True
        self.cap_ethtool = False
        self.settings = {
            'ifname': name,
        }
        self.settings.update(link)
        self.ethtool = None
        self.vrrp = vrrp
        if brport:
            self.brport = BRPort(name, brport)
        else:
            self.brport = None
        self.attr_map = {
            'kind': ['IFLA_LINKINFO', 'IFLA_INFO_KIND'],
        }
        self.attr_idx = ['link', 'master', 'gre_link',
                         'ip6gre_link', 'vxlan_link', 'xfrm_link']
        self.idx = None

        if 'address' in self.settings:
            self.settings['address'] = self.settings['address'].lower()
            self.idx = next(iter(ipr.link_lookup(
                address=self.settings['address'])), None)
        if 'permaddr' in self.settings:
            self.settings['permaddr'] = self.settings['permaddr'].lower()
            self.idx = ipr.get_iface_by_permaddr(self.settings['permaddr'])
        if 'businfo' in self.settings:
            self.settings['businfo'] = self.settings['businfo'].lower()
            self.idx = ipr.get_iface_by_businfo(self.settings['businfo'])

        for attr, mappings in self.attr_value_maps.items():
            if attr in self.settings and type(self.settings[attr]) != int:
                self.settings[attr] = next((k for k, v in mappings.items(
                ) if v == self.settings[attr]), self.settings[attr])

        for attr, lookup in self.attr_value_lookup.items():
            if attr in self.settings and type(self.settings[attr]) != int:
                try:
                    self.settings[attr] = lookup.lookup_id(self.settings[attr])
                except KeyError as err:
                    # mapping not available - catch exception and skip it
                    logger.warning('ignoring unknown group "%s"', self.settings[attr],
                                   extra={'iface': self.settings['ifname']})
                    del(self.settings[attr])

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
        if key in ["state", "permaddr", "businfo"]:
            if key in self.iface:
                return self.iface[key]
            else:
                return None

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

            try:
                with open(fn) as fh:
                    obj = yaml.load(fh, Loader=yaml.SafeLoader)
                    if type(obj) == dict:
                        ethtool[setting] = obj
            except Exception as err:
                logger.warning('parsing {} failed: {}'.format(
                    fn, err))

        return ethtool

    def fmt_ethtool_opt(self, value):
        if type(value) == bool:
            return {True: ["on"], False: ["off"]}[value]

        if type(value) == list:
            r = []
            for v in value:
                r += self.fmt_ethtool_opt(v)
            return r

        return [str(value)]

    def set_ethtool_state(self, ifname, settings, do_apply):
        if len(settings) == 0:
            return

        logger.info(
            'change (ethtool)', extra={'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_CHG})

        if not do_apply:
            return

        for setting in settings:
            cmd = [ethtool_path]
            if setting in ['coalesce', 'features', 'pause', 'rxfh']:
                cmd.append("--{}".format(setting))
            elif setting in ['nfc']:
                cmd.append("--config-{}".format(setting))
            else:
                cmd.append("--set-{}".format(setting))
            cmd.append(ifname)
            for option, value in self.ethtool[setting].items():
                cmd.extend([option] + self.fmt_ethtool_opt(value))
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
            try:
                with open(fn, 'w') as fh:
                    yaml.dump(self.ethtool[setting], fh)
            except Exception as err:
                logger.warning('failed write `{}`: {}'.format(fn, err.args[1]))

    def has_vrrp(self):
        return not self.vrrp is None

    def match_vrrp_select(self, vrrp_type, vrrp_name):
        return self.has_vrrp() and (self.vrrp['type'] == vrrp_type) and (self.vrrp['name'] == vrrp_name)

    def match_vrrp_state(self, vrrp_type, vrrp_name, vrrp_state):
        return self.match_vrrp_select(vrrp_type, vrrp_name) and (vrrp_state in self.vrrp['states'])

    def apply(self, do_apply, sysctl):
        excpts = ExceptionCollector(self.settings['ifname'])
        osettings = copy.deepcopy(self.settings)

        # lookup for attributes requiring a interface index
        for attr in self.attr_idx:
            if attr in self.settings:
                self.settings[attr] = next(iter(ipr.link_lookup(
                    ifname=self.settings[attr])), self.settings[attr])

        if self.idx is None:
            self.idx = next(iter(ipr.link_lookup(
                ifname=self.settings['ifname'])), None)

        if self.idx is not None:
            self.iface = next(iter(ipr.get_links(self.idx)), None)
            permaddr = ipr.get_permaddr(self.iface.get_attr('IFLA_IFNAME'))
            if not permaddr is None:
                self.iface['permaddr'] = permaddr
            businfo = ipr.get_businfo(self.iface.get_attr('IFLA_IFNAME'))
            if not businfo is None:
                self.iface['businfo'] = businfo

            # check for ifname collisions
            idx = next(iter(ipr.link_lookup(
                ifname=self.settings['ifname'])), None)
            if idx is not None and idx != self.idx and do_apply:
                try:
                    ipr.link('set', index=idx, state='down')
                    ipr.link('set', index=idx, ifname='{}!'.format(
                        self.settings['ifname']))
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, state='down', ifname='{}!')

            if self.cap_create and self.get_if_attr('kind') != self.settings['kind']:
                self.recreate(do_apply, sysctl, excpts)
            else:
                excpts.set_quiet(self.cap_create)
                self.update(do_apply, sysctl, excpts)
                if self.cap_create and list(excpts.get_all(lambda x: x['op'] != 'brport')):
                    excpts.reset()
                    self.recreate(do_apply, sysctl, excpts)
        else:
            self.create(do_apply, sysctl, excpts)

        self.settings = osettings
        return excpts

    def create(self, do_apply, sysctl, excpts, oper="add"):
        logger.info(
            oper, extra={'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_CHG})

        logger.debug("ip link add: {}".format(
            " ".join("{}={}".format(k, v) for k, v in self.settings.items())))
        if do_apply:
            try:
                # set state later
                state = self.settings.pop('state', None)

                # prevent altname conflict
                self.prevent_altname_conflict()

                # add link
                ipr.link('add', **(self.settings))
                self.idx = next(iter(ipr.link_lookup(
                    ifname=self.settings['ifname'])), None)

                if self.idx is not None:
                    # set sysctl settings if required
                    sysctl.apply(self.settings['ifname'], do_apply)

                    # set brport settings if required
                    if self.brport:
                        if self.brport.has_changes(self.idx):
                            self.brport.apply(do_apply, self.idx, excpts)

                    # set state if required
                    if state is not None and not excpts.has_op('brport'):
                        try:
                            ipr.link('set', index=self.idx, state=state)
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            excpts.add('set', err, state=state)
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                excpts.add('add', err, **(self.settings))

        if not self.ethtool is None:
            logger.debug("ethtool: {}".format(self.ethtool))
            self.set_ethtool_state(
                self.settings['ifname'], self.ethtool.keys(), do_apply)

    def recreate(self, do_apply, sysctl, excpts):
        logger.debug('has wrong link kind %s, removing', self.settings['kind'], extra={
                     'iface': self.settings['ifname']})
        if do_apply:
            try:
                ipr.link('del', index=self.idx)
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                excpts.add('del', err)
        self.idx = None
        self.create(do_apply, ifstate, excpts, "replace")

    def update(self, do_apply, sysctl, excpts):
        logger.debug('checking link', extra={'iface': self.settings['ifname']})

        old_state = self.iface['state']
        has_link_changes = False
        has_state_changes = False
        for setting in self.settings.keys():
            logger.debug('  %s: %s => %s', setting, self.get_if_attr(
                setting), self.settings[setting], extra={'iface': self.settings['ifname']})
            if setting == "state":
                has_state_changes = self.get_if_attr(
                    setting) != self.settings[setting]
            else:
                if setting != 'kind' or self.cap_create:
                    has_link_changes |= self.get_if_attr(
                        setting) != self.settings[setting]

        has_ethtool_changes = set()
        if not self.ethtool is None:
            logger.debug('checking ethtool', extra={
                         'iface': self.settings['ifname']})
            ethtool = self.get_ethtool_state(self.ethtool.keys())
            if ethtool is None:
                has_ethtool_changes.add(self.ethtool.keys())
            else:
                for setting, options in self.ethtool.items():
                    if not setting in ethtool:
                        has_ethtool_changes.add(setting)
                    else:
                        for option in options.keys():
                            logger.debug('  %s.%s: %s => %s', setting, option, ethtool[setting].get(
                                option), self.ethtool[setting][option], extra={'iface': self.settings['ifname']})
                            if self.ethtool[setting][option] != ethtool[setting].get(option):
                                has_ethtool_changes.add(setting)

        has_brport_changes = False
        if self.brport:
            has_brport_changes = self.brport.has_changes(self.idx)

        if has_link_changes:
            logger.debug('needs to be configured', extra={
                         'iface': self.settings['ifname']})
            if old_state != 'down':
                logger.debug('shutting down', extra={
                             'iface': self.settings['ifname']})
                if do_apply:
                    try:
                        ipr.link('set', index=self.idx, state='down')
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        excpts.add('set', err, state='down')

                if not 'state' in self.settings:
                    self.settings['state'] = 'up'

            # set sysctl settings
            sysctl.apply(self.get_if_attr(
                'ifname'), do_apply, self.settings['ifname'])

            self.set_ethtool_state(self.get_if_attr(
                'ifname'), has_ethtool_changes, do_apply)

            has_ifname_change = self.get_if_attr(
                'ifname') != self.settings['ifname']
            if has_ifname_change:
                logger.info('change (was {})'.format(self.get_if_attr('ifname')), extra={
                            'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_CHG})
            else:
                logger.info('change', extra={
                            'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_CHG})

            logger.debug("ip link set: {}".format(
                " ".join("{}={}".format(k, v) for k, v in self.settings.items())))
            if do_apply:
                # temp. remove special settings
                state = self.settings.pop('state', None)
                peer = self.settings.pop('peer', None)

                if has_ifname_change:
                    self.prevent_altname_conflict()

                try:
                    ipr.link('set', index=self.idx, **(self.settings))
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, **(self.settings))

                # restore settings
                if state is not None:
                    self.settings['state'] = state
                if peer is not None:
                    self.settings['peer'] = peer

                try:
                    if not state is None:
                        # restore state setting for recreate
                        self.settings['state'] = state
                        ipr.link('set', index=self.idx, state=state)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, state=state)

            if has_brport_changes:
                self.brport.apply(do_apply, self.idx, excpts)
        else:
            # set sysctl settings
            sysctl.apply(self.get_if_attr(
                'ifname'), do_apply)

            self.set_ethtool_state(self.get_if_attr(
                'ifname'), has_ethtool_changes, do_apply)

            if has_brport_changes:
                if old_state:
                    logger.debug('shutting down', extra={
                                 'iface': self.settings['ifname']})
                    if do_apply:
                        try:
                            ipr.link('set', index=self.idx, state='down')
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            excpts.add('set', err, state='down')
                    if not 'state' in self.settings:
                        self.settings['state'] = 'up'

                    has_state_changes = self.settings['state'] == 'up'

                self.brport.apply(do_apply, self.idx, excpts)

            if has_state_changes:
                try:
                    ipr.link('set', index=self.idx,
                             state=self.settings["state"])
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, state=state)
                logger.info('change', extra={
                            'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_CHG})

            else:
                logger.info(
                    'ok', extra={'iface': self.settings['ifname'], 'style': IfStateLogging.STYLE_OK})

    def depends(self):
        deps = []
        for attr in self.attr_idx:
            if attr in self.settings:
                deps.append(self.settings[attr])

        if self.brport:
            deps.extend(self.brport.depends())

        return deps

    def prevent_altname_conflict(self):
        '''
        When renaming interfaces a interface name conflict could
        happen on the IFLA_ALT_IFNAME property (Linux 5.5+). Remove
        the altname from the other interface in such case, it may be
        the same interface if it is renamed to one of it's altnames.
        '''

        logger.debug('checking altname conflict', extra={
                     'iface': self.settings['ifname']})

        # get link candidate having the ifname as altname
        try:
            link = next(
                iter(ipr.link('get', altname=self.settings['ifname'])), None)
        except Exception as err:
            if not isinstance(err, netlinkerror_classes):
                raise
            return

        # pyroute2 may return the interface having ifname rather than
        # altname set - only remove altname if it is set
        properties = link.get_attr('IFLA_PROP_LIST')
        if properties is not None and self.settings['ifname'] in properties.get_attrs('IFLA_ALT_IFNAME'):
            logger.debug('  found: %s (%d)', link.get_attr(
                'IFLA_IFNAME'), link['index'], extra={'iface': self.settings['ifname']})
            try:
                ipr.link('property_del',
                         index=link['index'], altname=self.settings['ifname'])
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise

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
    def __init__(self, name, link, ethtool, vrrp, brport):
        super().__init__(name, link, ethtool, vrrp, brport)
