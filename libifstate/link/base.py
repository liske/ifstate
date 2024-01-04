from libifstate.util import logger, IfStateLogging, LinkDependency
from libifstate.exception import ExceptionCollector, LinkTypeUnknown, netlinkerror_classes
from libifstate.brport import BRPort
from libifstate.routing import RTLookups
from abc import ABC, abstractmethod
import os
import subprocess
import yaml
import shutil
import copy
import pyroute2.netns

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
        # === tuntap ===
        'tun_type': {
            1: 'tun',
            2: 'tap',
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
    attr_bind_kinds = [
        'ip6tnl',
        'tun',
        'veth',
        'vti',
        'vti6',
        'vxlan',
        'ipip',
        'gre',
        'gretap',
        'ip6gre',
        'ip6gretap',
        'geneve',
        'wireguard',
        'xfrm',
    ]

    def __new__(cls, *args, **kwargs):
        cname = cls.__name__
        if cname == Link.__name__:
            cname = "{}Link".format(args[3]['kind'].lower().capitalize())

        for c in Link.__subclasses__():
            if c.__name__ == cname:
                return super().__new__(c)

        return super().__new__(GenericLink)
        #raise LinkTypeUnknown()

    def __init__(self, ifstate, netns, name, link, ethtool, vrrp, brport):
        self.ifstate = ifstate
        self.netns = netns
        self.cap_create = True
        self.cap_ethtool = False
        self.settings = {
            'ifname': name,
        }
        self.settings.update(link)
        self.ethtool = None
        self.vrrp = vrrp
        if brport:
            self.brport = BRPort(netns, name, brport)
        else:
            self.brport = None
        self.attr_map = {
            'kind': ['IFLA_LINKINFO', 'IFLA_INFO_KIND'],
        }
        self.attr_idx = ['link', 'master', 'gre_link',
                         'ip6gre_link', 'vxlan_link', 'xfrm_link']
        self.idx = None
        self.link_registry_search_args = []
        self.link_ref = LinkDependency(name, self.netns.netns)

        # prepare link registry search filters
        if 'businfo' in self.settings:
            self.settings['businfo'] = self.settings['businfo'].lower()
            self.link_registry_search_args.append({
                'kind': self.settings['kind'],
                'businfo': self.settings['businfo'],
            })

        if 'permaddr' in self.settings:
            self.settings['permaddr'] = self.settings['permaddr'].lower()
            self.link_registry_search_args.append({
                'kind': self.settings['kind'],
                'permaddr': self.settings['permaddr'],
            })

        if 'address' in self.settings and self.settings['kind'] == 'physical':
            self.settings['address'] = self.settings['address'].lower()
            self.link_registry_search_args.append({
                'kind': self.settings['kind'],
                'address': self.settings['address'],
                'netns': netns.netns,
            })

        self.link_registry_search_args.append({
            'kind': self.settings['kind'],
            'ifname': name,
            'netns': netns.netns,
        })

        if self.settings['kind'] == 'physical':
            self.link_registry_search_args.append({
                'kind': 'physical',
                'ifname': name,
                'orphan': True,
            })

        self.search_link_registry()

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
                                   extra={'iface': self.settings['ifname'], 'netns': self.netns})
                    del(self.settings[attr])

        if self.settings['kind'] in self.attr_bind_kinds:
            if not 'bind_netns' in self.settings:
                logger.debug('set bind_netns to current netns',
                             extra={'iface': self.settings['ifname'], 'netns': self.netns})
                self.bind_netns = self.netns.netns
            else:
                self.bind_netns = self.settings['bind_netns']
        elif 'bind_netns' in self.settings:
            logger.warning('Ignoring not supported link attribute "bind_netns" for %s link.',
                           self.settings['kind'],
                           extra={'iface': self.settings['ifname'], 'netns': self.netns})
        if 'bind_netns' in self.settings:
            del(self.settings['bind_netns'])

    def search_link_registry(self):
        for args in self.link_registry_search_args:
            item = self.ifstate.link_registry.get_link(**args)
            if item is not None:
                item.link = self
                return item

        logger.debug('no link found: %s', self.link_registry_search_args,
                     extra={'iface': self.settings['ifname'], 'netns': self.netns})

        return None

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
        try:
            os.makedirs("/run/libifstate/ethtool", exist_ok=True)
        except:
            pass

        # try to create a unique netns independent filename
        name = ('bi', self.iface.get('businfo'))
        if None in name:
            name = ('pa', self.iface.get('permaddr'))
        if None in name:
            name = ('id', str(self.idx))
        name = "__".join(name)

        return "/run/libifstate/ethtool/{}__{}.state".format(name, setting)

    def get_ethtool_state(self, settings):
        ethtool = {}

        for setting in settings:
            ethtool[setting] = {}
            fn = self.get_ethtool_fn(setting)

            if not os.path.isfile(fn):
                logger.debug('no prior ethtool %s state available', setting,
                             extra={'iface': self.settings['ifname'], 'netns': self.netns})
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

    def fmt_ethtool_opt(self, setting, option, value):
        if type(value) == bool:
            return {True: ["on"], False: ["off"]}[value]

        if type(value) == list:
            r = []
            for v in value:
                r += self.fmt_ethtool_opt(setting, option, v)
            return r

        # quirk for ethtool --set-change advertise: it requires hex
        if type(value) == int and setting == 'change' and option == 'advertise':
            return[hex(value)]

        return [str(value)]

    def set_ethtool_state(self, ifname, settings, do_apply):
        if len(settings) == 0:
            return

        logger.log_change('ethtool')

        if not do_apply:
            return

        for setting in settings:
            cmd = [ethtool_path]
            if setting in ['change', 'coalesce', 'features', 'pause', 'rxfh']:
                cmd.append("--{}".format(setting))
            elif setting in ['nfc']:
                cmd.append("--config-{}".format(setting))
            else:
                cmd.append("--set-{}".format(setting))
            cmd.append(ifname)
            for option, value in self.ethtool[setting].items():
                cmd.extend([option] + self.fmt_ethtool_opt(setting, option, value))
            logger.debug("{}".format(" ".join(cmd)))

            if self.netns.netns is not None:
                pyroute2.netns.pushns(self.netns.netns)
            try:
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
            finally:
                if self.netns.netns is not None:
                    pyroute2.netns.popns()

            fn = self.get_ethtool_fn(setting)
            try:
                with open(fn, 'w') as fh:
                    yaml.dump(self.ethtool[setting], fh)
            except IOError as err:
                logger.warning('failed write `{}`: {}'.format(fn, err.args[1]))

    def get_bind_fn(self, netns_name, idx):
        if netns_name is None:
            dirname = "/run/libifstate/bind"
        else:
            dirname = "/run/libifstate/netns/{}/bind".format(netns_name)

        try:
            os.makedirs(dirname, exist_ok=True)
        except:
            pass

        return "{}/{}.mount".format(dirname, idx)

    def set_bind_state(self, state):
        fn = self.get_bind_fn(self.netns.netns, self.idx)
        try:
            with open(fn, 'wb') as fh:
                fh.write(state)
        except IOError as err:
            logger.warning('failed write `{}`: {}'.format(fn, err.args[1]))

    def get_bind_netns(self):
        if not hasattr(self, 'bind_netns'):
            return None

        if self.bind_netns is None:
            return self.ifstate.root_netns

        return self.ifstate.namespaces.get(self.bind_netns)

    def bind_needs_recreate(self, item):
        if not item.attributes['kind'] in self.attr_bind_kinds:
            return False

        bind_netns = self.get_bind_netns()
        if bind_netns is None:
            logger.warning('bind_netns "%s" is unknown',
                        self.bind_netns,
                        extra={
                            'iface': self.settings['ifname'],
                            'netns': self.netns})
            return False

        fn = self.get_bind_fn(item.netns.netns, item.index)
        try:
            with open(fn, 'rb') as fh:
                state = fh.read()
        except IOError:
            logger.debug('no bind_netns state available',
                extra={'iface': self.settings['ifname'], 'netns': self.netns})
            return True

        logger.debug(f'bind_netns differ: {state} != {bind_netns.mount}',
            extra={'iface': self.settings['ifname'], 'netns': self.netns})

        return state != bind_netns.mount

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
            if self.settings.get(attr) is not None:
                netns_attr = "{}_netns".format(attr)
                netnsid_attr = "{}_netnsid".format(attr)
                if netns_attr in self.settings:
                    # ToDo: throw exception for unknown netns
                    (peer_ipr, peer_nsid) = self.netns.get_netnsid(self.settings[netns_attr])
                    self.settings[netnsid_attr] = peer_nsid
                    idx = next(iter(peer_ipr.link_lookup(
                        ifname=self.settings[attr])), None)

                    del(self.settings[netns_attr])
                else:
                    idx = next(iter(self.netns.ipr.link_lookup(
                        ifname=self.settings[attr])), None)

                if idx is not None:
                    self.settings[attr] = idx
                else:
                    logger.warning('could not find %s "%s"', attr,
                        self.settings[attr],
                        extra={
                            'iface': self.settings['ifname'],
                            'netns': self.netns})
                    self.settings['state'] = 'down'
                    if netnsid_attr in self.settings:
                        del(self.settings[netnsid_attr])
                    del(self.settings[attr])
            elif attr in self.settings:
                # unset index references have a None state,
                # but configuration requires the invalid ifindex 0
                self.settings[attr] = 0

        # get interface from registry
        item = self.search_link_registry()

        # check if bind_netns option requires a recreate
        if item is not None and self.bind_needs_recreate(item):
            self.idx = item.index
            self.recreate(do_apply, sysctl, excpts)

            self.settings = osettings
            return excpts

        # move interface into netns if required
        if item is not None and item.netns.netns != self.netns.netns:
            logger.log_change('netns')

            if do_apply:
                try:
                    # move link into target netns
                    item.update_netns(self.netns)
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    item.netns.ipr.link('set', index=item.attributes['index'], state='down')
                    excpts.add('set', err, netns=self.netns.netns)
                    return excpts

        if item is not None:
            self.idx = item.index

        if self.idx is not None:
            self.iface = next(iter(item.netns.ipr.get_links(self.idx)), None)
            permaddr = item.netns.ipr.get_permaddr(self.iface.get_attr('IFLA_IFNAME'))
            if not permaddr is None:
                self.iface['permaddr'] = permaddr
            businfo = item.netns.ipr.get_businfo(self.iface.get_attr('IFLA_IFNAME'))
            if not businfo is None:
                self.iface['businfo'] = businfo

            # check for ifname collisions
            idx = next(iter(self.netns.ipr.link_lookup(
                ifname=self.settings['ifname'])), None)
            if idx is not None and idx != self.idx and do_apply:
                try:
                    self.netns.ipr.link('set', index=idx, state='down')
                    self.netns.ipr.link('set', index=idx, ifname='{}!'.format(
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
        logger.log_add('link', oper)

        settings = copy.deepcopy(self.settings)
        bind_netns = self.get_bind_netns()
        if bind_netns is not None and bind_netns.netns != self.netns.netns:
            logger.debug("handle link binding", extra={
                'iface': self.settings['ifname'],
                'netns': self.netns})
            settings['ifname'] = self.ifstate.gen_unique_ifname()

        logger.debug("ip link add: {}".format(
            " ".join("{}={}".format(k, v) for k, v in settings.items())))
        if do_apply:
            try:
                # set master and state later
                master = settings.pop('master', None)
                state = settings.pop('state', None)

                # prevent altname conflict
                self.prevent_altname_conflict()

                # add link
                if bind_netns is None or bind_netns.netns == self.netns.netns:
                    self.netns.ipr.link('add', **(settings))
                    link = next(iter(self.netns.ipr.get_links(
                                ifname=settings['ifname'])), None)
                    if link is not None:
                        item = self.ifstate.link_registry.add_link(self.netns, link)
                # add and move link
                else:
                    bind_netns.ipr.link('add', **(settings))
                    link = next(iter(bind_netns.ipr.get_links(
                                ifname=settings['ifname'])), None)
                    if link is not None:
                        item = self.ifstate.link_registry.add_link(bind_netns, link)
                        item.update_netns(self.netns)
                        item.update_ifname(self.settings['ifname'])

                self.idx = next(iter(self.netns.ipr.link_lookup(
                    ifname=self.settings['ifname'])), None)

                if self.idx is not None:
                    if bind_netns is not None:
                        self.set_bind_state(bind_netns.mount)

                    # set sysctl settings if required
                    sysctl.apply(self.settings['ifname'], do_apply)

                    # set brport settings if required
                    if self.brport:
                        if self.brport.has_changes(self.idx):
                            self.brport.apply(do_apply, self.idx, excpts)

                    # set master and state if required
                    if not excpts.has_op('brport'):
                        if master is not None:
                            try:
                                self.netns.ipr.link('set', index=self.idx, master=master)
                            except Exception as err:
                                if not isinstance(err, netlinkerror_classes):
                                    raise
                                excpts.add('set', err, master=master)
                        if state is not None:
                            try:
                                self.netns.ipr.link('set', index=self.idx, state=state)
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
        logger.debug('needs to be recreated', extra={
                     'iface': self.settings['ifname'], 'netns': self.netns})
        if do_apply:
            try:
                self.netns.ipr.link('del', index=self.idx)
            except Exception as err:
                if not isinstance(err, netlinkerror_classes):
                    raise
                excpts.add('del', err)
        self.idx = None
        self.create(do_apply, sysctl, excpts, "replace")

    def update(self, do_apply, sysctl, excpts):
        logger.debug('checking link', extra={'iface': self.settings['ifname'], 'netns': self.netns})

        old_state = self.iface['state']
        has_link_changes = False
        has_state_changes = False
        for setting in self.settings.keys():
            differs = False

            if setting == "state":
                differs = self.get_if_attr(
                    setting) != self.settings[setting]
                has_state_changes = differs
            elif setting in self.attr_idx:
                # unset index references have a None state,
                # but configuration requires the invalid ifindex 0
                differs = (self.get_if_attr(setting) or 0) != self.settings[setting]
                has_link_changes |= differs
            else:
                if setting != 'kind' or self.cap_create:
                    differs = self.get_if_attr(setting) != self.settings[setting]
                    has_link_changes |= differs

            logger.debug('  %s: %s %s %s',
                setting,
                self.get_if_attr(setting),
                ('!=' if differs else '=='),
                self.settings[setting],
                extra={'iface': self.settings['ifname'], 'netns': self.netns})

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
                         'iface': self.settings['ifname'], 'netns': self.netns})
            if old_state != 'down':
                logger.debug('shutting down', extra={
                             'iface': self.settings['ifname'], 'netns': self.netns})
                if do_apply:
                    try:
                        self.netns.ipr.link('set', index=self.idx, state='down')
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
                logger.log_change('ifname')
            logger.log_change('link')

            logger.debug("ip link set: {}".format(
                " ".join("{}={}".format(k, v) for k, v in self.settings.items())))
            if do_apply:
                # temp. remove special settings
                skipped_settings = {}
                for setting in ['state', 'peer', 'kind', 'businfo', 'permaddr']:
                    if setting in self.settings:
                        skipped_settings[setting] = self.settings.pop(setting)

                if has_ifname_change:
                    self.prevent_altname_conflict()

                try:
                    self.netns.ipr.link('set', index=self.idx, **(self.settings))
                    self.iface = next(iter(self.netns.ipr.get_links(self.idx)), None)

                    for setting in self.settings.keys():
                        if not setting.endswith('_netns') or not setting[:-6] in self.attr_idx:
                            value = self.get_if_attr(setting)

                            if setting in self.attr_idx and value is None:
                                # None index references are configuration via the invalid ifindex 0
                                value = 0

                            if value != self.settings[setting]:
                                if self.cap_create:
                                    logger.debug('  %s: setting could not be changed', setting, extra={'iface': self.settings['ifname']})
                                    excpts.add('set', Exception('ip link set'), **{setting: self.settings[setting]})
                                else:
                                    logger.warning('%s setting could not be changed', setting,
                                                   extra={'iface': self.settings['ifname']})
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, **(self.settings))

                # restore settings
                for setting, value in skipped_settings.items():
                    self.settings[setting] = value

                try:
                    if 'state' in self.settings:
                        # restore state setting for recreate
                        self.netns.ipr.link('set', index=self.idx, state=self.settings['state'])
                except Exception as err:
                    if not isinstance(err, netlinkerror_classes):
                        raise
                    excpts.add('set', err, state=self.settings['state'])

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
                            self.netns.ipr.link('set', index=self.idx, state='down')
                        except Exception as err:
                            if not isinstance(err, netlinkerror_classes):
                                raise
                            excpts.add('set', err, state='down')
                    if not 'state' in self.settings:
                        self.settings['state'] = 'up'

                    has_state_changes = self.settings['state'] == 'up'

                self.brport.apply(do_apply, self.idx, excpts)

            if has_state_changes:
                if do_apply:
                    try:
                        self.netns.ipr.link('set', index=self.idx,
                                 state=self.settings["state"])
                    except Exception as err:
                        if not isinstance(err, netlinkerror_classes):
                            raise
                        excpts.add('set', err, state=self.settings['state'])
                logger.log_change('link')
            else:
                logger.log_ok('link')

    def depends(self):
        deps = []

        for attr in self.attr_idx:
            if self.settings.get(attr) is not None:
                ns = self.settings.get("{}_netns".format(attr), self.netns.netns)
                deps.append(LinkDependency(self.settings[attr], ns))

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
                     'iface': self.settings['ifname'], 'netns': self.netns})

        # get link candidate having the ifname as altname
        try:
            link = next(
                iter(self.netns.ipr.link('get', altname=self.settings['ifname'])), None)
        except Exception as err:
            if not isinstance(err, netlinkerror_classes):
                raise
            return

        # pyroute2 may return the interface having ifname rather than
        # altname set - only remove altname if it is set
        properties = link.get_attr('IFLA_PROP_LIST')
        if properties is not None and self.settings['ifname'] in properties.get_attrs('IFLA_ALT_IFNAME'):
            logger.debug('  found: %s (%d)', link.get_attr(
                'IFLA_IFNAME'), link['index'], extra={'iface': self.settings['ifname'], 'netns': self.netns})
            try:
                self.netns.ipr.link('property_del',
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
    def __init__(self, ifstate, netns, name, link, ethtool, vrrp, brport):
        super().__init__(ifstate, netns, name, link, ethtool, vrrp, brport)
