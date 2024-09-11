import subprocess
from enum import Enum
from pathlib import Path
from typing import (
    Any, Iterator, List, Mapping, MutableMapping, Optional, Union
)

from pylspci.device import Device
from pylspci.fields import PCIAccessParameter
from pylspci.filters import DeviceFilter, SlotFilter
from pylspci.parsers.base import Parser

OptionalPath = Optional[Union[str, Path]]


class IDResolveOption(Enum):
    """
    ``lspci`` device, vendor, class names outputting options.
    """

    NameOnly = ''
    """
    Only output the names.
    """

    IDOnly = '-n'
    """
    Only output the hexadecimal IDs.
    This is the only option that does not require a ``pciids`` file.
    """

    Both = '-nn'
    """
    Output both the names and hexadecimal IDs, in the format ``Name [ID]``.
    """


def lspci(
        pciids: OptionalPath = None,
        pcimap: OptionalPath = None,
        access_method: Optional[str] = None,
        pcilib_params: Mapping[str, Any] = {},
        file: OptionalPath = None,
        verbose: bool = False,
        kernel_drivers: bool = False,
        bridge_paths: bool = False,
        hide_single_domain: bool = True,
        id_resolve_option: IDResolveOption = IDResolveOption.Both,
        slot_filter: Optional[Union[SlotFilter, str]] = None,
        device_filter: Optional[Union[DeviceFilter, str]] = None,
        ) -> str:
    """
    Call the ``lspci`` command with various parameters.

    :param pciids: An optional path to a ``pciids`` file,
       to convert hexadecimal class, vendor or device IDs into names.
    :type pciids: str or Path or None
    :param pcimap: An optional path to a ``pcimap`` file,
       linking Linux kernel modules and their supported PCI IDs.
    :type pcimap: str or Path or None
    :param access_method: The access method to use to find devices.
       Set this to ``help`` to list the available access methods in a
       human-readable format. For the machine-readable format, see
       :func:`list_access_methods`.
    :type access_method: str or None
    :param pcilib_params: Parameters passed to pcilib's access methods.
       To list the available parameters with their description and default
       values, see :func:`list_pcilib_params`.
    :type pcilib_params: Mapping[str, Any] or None
    :param file: An hexadecimal dump from ``lspci -x`` to load data from,
       instead of accessing real hardware.
    :type file: str or Path or None
    :param bool verbose: Increase verbosity.
       This radically changes the output format.
    :param bool kernel_drivers: Also include kernel modules and drivers
       in the output. Only has effect with the verbose output.
    :param bool bridge_paths: Add PCI bridge paths to slot numbers.
    :param bool hide_single_domain: If there is a single PCI domain on this
       machine and it is numbered ``0000``, hide it from the slot numbers.
    :param id_resolve_option: Device, vendor or class ID outputting mode.
       See the :class:`IDResolveOption` docs for more details.
    :type id_resolve_option: IDResolveOption
    :param slot_filter: Filter devices by their slot
      (domain, bus, device, function)
    :type slot_filter: SlotFilter or str or None
    :param device_filter: Filter devices by their vendor, device or class ID
    :type device_filter: DeviceFilter or str or None
    :return: Any output from the ``lspci`` command.
    :rtype: str
    :raises subprocess.CalledProcessError:
       ``lspci`` returned a non-zero error code.
    """
    args: List[str] = ['lspci', '-mm']
    if verbose:
        args.append('-vvv')
    if kernel_drivers:
        args.append('-k')
    if bridge_paths:
        args.append('-PP')
    if not hide_single_domain:
        args.append('-D')
    if access_method:
        args.append('-A{}'.format(access_method))
    if slot_filter:
        if isinstance(slot_filter, str):
            slot_filter = SlotFilter.parse(slot_filter)
        args.append('-s')
        args.append(str(slot_filter))
    if device_filter:
        if isinstance(device_filter, str):
            device_filter = DeviceFilter.parse(device_filter)
        args.append('-d')
        args.append(str(device_filter))
    if id_resolve_option != IDResolveOption.NameOnly:
        args.append(id_resolve_option.value)

    if pciids:
        args.append('-i')
        if not isinstance(pciids, Path):
            pciids = Path(pciids)
        assert pciids.is_file(), 'ID database file not found'
        args.append(str(pciids.absolute()))

    if pcimap:
        args.append('-p')
        if not isinstance(pcimap, Path):
            pcimap = Path(pcimap)
        assert pcimap.is_file(), 'Kernel module mapping file not found'
        args.append(str(pcimap.absolute()))

    if file:
        args.append('-F')
        if not isinstance(file, Path):
            file = Path(file)
        assert file.is_file(), 'Hex dump file not found'
        args.append(str(file.absolute()))

    for key, value in pcilib_params.items():
        args.append('-O{}={}'.format(key, value))

    return subprocess.check_output(
        args,
        universal_newlines=True,
    )


def list_access_methods() -> List[str]:
    """
    Calls ``lspci(access_method='help')`` to list the PCI access methods
    the underlying ``pcilib`` provides and parses the human-readable list into
    a machine-readable list.

    :returns: A list of access methods.
    :rtype: List[str]
    :raises subprocess.CalledProcessError:
       ``lspci`` returned a non-zero error code.
    """
    return list(filter(
        lambda line: line and 'Known PCI access methods' not in line,
        map(str.strip, lspci(access_method='help').splitlines()),
    ))


def list_pcilib_params_raw() -> List[str]:
    """
    Calls ``lspci -Ohelp`` to list the PCI access parameters the underlying
    ``pcilib`` provides.

    :returns: A list of available PCI access parameters.
    :rtype: List[str]
    :raises subprocess.CalledProcessError:
       ``lspci`` returned a non-zero error code.
    """
    return list(filter(
        lambda line: line and 'Known PCI access parameters' not in line,
        map(str.strip, subprocess.check_output(
            ['lspci', '-Ohelp'],
            universal_newlines=True,
        ).splitlines())
    ))


def list_pcilib_params() -> List[PCIAccessParameter]:
    """
    Calls ``lspci -Ohelp`` to list the PCI access parameters the underlying
    ``pcilib`` provides and parse the human-readable list into
    a machine-readable list.

    :returns: A list of available PCI access parameters.
    :rtype: List[PCIAccessParameter]
    :raises subprocess.CalledProcessError:
       ``lspci`` returned a non-zero error code.
    """
    return list(map(PCIAccessParameter, list_pcilib_params_raw()))


class CommandBuilder(object):
    """
    Helper class to build a lspci call using a Builder pattern.

    Iterating over the builder will result in the command being called,
    and will return strings, devices or pcilib parameters, one at a time,
    depending on the parsing settings.
    """

    _list_access_methods: bool = False
    _list_pcilib_params: bool = False
    _list_pcilib_params_raw: bool = False
    _params: MutableMapping[str, Any] = {}
    _parser: Optional[Parser] = None

    def __init__(self, **kwargs: Any):
        self._params = kwargs

    def __iter__(self) -> Iterator[Union[str, Device, PCIAccessParameter]]:
        result: Union[str, List[str], List[Device], List[PCIAccessParameter]]
        if self._list_access_methods:
            result = list_access_methods()
        elif self._list_pcilib_params:
            if self._list_pcilib_params_raw:
                result = list_pcilib_params_raw()
            else:
                result = list_pcilib_params()
        elif self._parser:
            result = self._parser.parse(lspci(**self._params))
        else:
            result = lspci(**self._params)

        if isinstance(result, str):
            return iter([result, ])
        return iter(result)

    def use_pciids(self,
                   path: OptionalPath,
                   check: bool = True) -> 'CommandBuilder':
        """
        Use a PCI IDs file from a given path.

        :param path: A string or path-like object pointing to the PCI IDs file
           to use. Set to None to use the default files from lspci.
        :type path: str or Path or None
        :param bool check: Whether to check for the file's existence
           immediately, or delay that to the lspci invocation.
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if path:
            if not isinstance(path, Path):
                path = Path(path)
            if check:
                assert path.is_file(), 'ID database file not found'
        self._params['pciids'] = path
        return self

    def use_pcimap(self,
                   path: OptionalPath,
                   check: bool = True) -> 'CommandBuilder':
        """
        Use a kernel module mapping file from a given path.

        :param path: A string or path-like object pointing to the mapping file
           to use. Set to None to use the default files from lspci.
        :type path: str or Path or None
        :param bool check: Whether to check for the file's existence
           immediately, or delay that to the lspci invocation.
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if path:
            if not isinstance(path, Path):
                path = Path(path)
            if check:
                assert path.is_file(), 'Kernel module mapping file not found'
        self._params['pcimap'] = path
        return self

    def use_access_method(self, method: Optional[str]) -> 'CommandBuilder':
        """
        Use a specific access method to list all devices.

        :param method: Name of the access method to use. Set to None to use
           lspci's default method.
        :type method: str or None
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._params['access_method'] = method
        return self

    def list_access_methods(self, value: bool = True) -> 'CommandBuilder':
        """
        List the pcilib access methods instead of listing devices.

        :param value: Whether or not to list the access methods.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._list_access_methods = value
        if value:
            self._list_pcilib_params = False
        return self

    def list_pcilib_params(self,
                           value: bool = True,
                           raw: bool = False) -> 'CommandBuilder':
        """
        List the pcilib parameters instead of listing devices.

        :param value: Whether or not to list the pcilib parameters.
        :type value: bool
        :param raw: When listing the pcilib parameters, whether to return the
           raw strings or parse them into PCIAccessParameter instances.
        :type raw: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._list_pcilib_params = value
        self._list_pcilib_params_raw = raw
        if value:
            self._list_access_methods = False
        return self

    def with_pcilib_params(self,
                           *args: Mapping[str, Any],
                           **kwargs: Any) -> 'CommandBuilder':
        """
        Override some pcilib parameters. When given a dict, will rewrite the
        parameters with the new dict. When given keyword arguments, will update
        the existing parameters. Pass ``None`` or ``{}`` to reset all of the
        parameters.

        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if len(args) > 0:
            assert len(args) <= 1, 'Only one positional argument is allowed'
            assert not kwargs, 'Use either a dict or keyword arguments'
            self._params['pcilib_params'] = args[0]
            return self
        self._params.setdefault('pcilib_params', {}).update(kwargs)
        return self

    def from_file(self,
                  path: OptionalPath,
                  check: bool = True) -> 'CommandBuilder':
        """
        Use a hexadecimal dump from a previous run of lspci instead of
        accessing the host's devices directly.

        :param path: A string or path-like object pointing to the hex dump file
           to use. Set to None to not use a dump file.
        :type path: str or Path or None
        :param bool check: Whether to check for the file's existence
           immediately, or delay that to the lspci invocation.
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if path:
            if not isinstance(path, Path):
                path = Path(path)
            if check:
                assert path.is_file(), 'Hex dump file not found'
        self._params['file'] = path
        return self

    def verbose(self, value: bool = True) -> 'CommandBuilder':
        """
        Enable verbose mode.

        :param value: Whether or not to use verbose mode.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._params['verbose'] = value
        return self

    def include_kernel_drivers(self, value: bool = True) -> 'CommandBuilder':
        """
        Under Linux, includes the available kernel modules for each device.
        Implies ``.verbose()``.

        :param value: Whether or not to include the available kernel modules
           for each device.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._params['kernel_drivers'] = value
        if value:
            return self.verbose()
        return self

    def include_bridge_paths(self, value: bool = True) -> 'CommandBuilder':
        """
        Include the PCI bridge paths along with the IDs.
        Implies ``.with_ids()``.

        :param value: Whether or not to include the PCI bridge paths.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._params['bridge_paths'] = value
        if value:
            return self.with_ids()
        return self

    def hide_single_domain(self, value: bool = True) -> 'CommandBuilder':
        """
        Hide the domain numbers when there is only one domain, numbered zero.

        :param value: Whether or not to hide the domain numbers for a single
           domain.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._params['hide_single_domain'] = value
        return self

    def with_ids(self, value: bool = True) -> 'CommandBuilder':
        """
        Include PCI device IDs. If disabled, implies ``.with_names()``.

        :param value: Whether or not to include the PCI device IDs.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if value:
            if self._params.get('id_resolve_option') == \
                    IDResolveOption.NameOnly:
                self._params['id_resolve_option'] = IDResolveOption.Both
        else:
            self._params['id_resolve_option'] = IDResolveOption.NameOnly
        return self

    def with_names(self, value: bool = True) -> 'CommandBuilder':
        """
        Include PCI device names. If disabled, implies ``.with_ids()``.

        :param value: Whether or not to include the PCI device names.
        :type value: bool
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if value:
            if self._params.get('id_resolve_option') == IDResolveOption.IDOnly:
                self._params['id_resolve_option'] = IDResolveOption.Both
        else:
            self._params['id_resolve_option'] = IDResolveOption.IDOnly
        return self

    def slot_filter(self,
                    *args: str,
                    domain: Optional[int] = None,
                    bus: Optional[int] = None,
                    device: Optional[int] = None,
                    function: Optional[int] = None) -> 'CommandBuilder':
        """
        Filter the devices geographically.
        Can be passed a string in lspci's filter syntax, or keyword arguments
        for each portion of the filter.
        See :class:`pylspci.filters.SlotFilter`.

        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if len(args) > 0:
            assert len(args) <= 1, 'Only one positional argument allowed'
            assert not domain and not bus and not device and not function, \
                'Use either a string value or the domain, bus, device ' \
                'and function keyword arguments'
            self._params['slot_filter'] = SlotFilter.parse(args[0])
        else:
            self._params['slot_filter'] = SlotFilter(
                domain=domain,
                bus=bus,
                device=device,
                function=function,
            )
        return self

    def device_filter(self,
                      *args: str,
                      cls: Optional[int] = None,
                      vendor: Optional[int] = None,
                      device: Optional[int] = None) -> 'CommandBuilder':
        """
        Filter the devices logically.
        Can be passed a string in lspci's filter syntax, or keyword arguments
        for each portion of the filter.
        See :class:`pylspci.filters.DeviceFilter`.

        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if len(args) > 0:
            assert len(args) <= 1, 'Only one positional argument allowed'
            assert not cls and not vendor and not device, \
                'Use either a string value or the cls, vendor and device ' \
                'keyword arguments'
            self._params['device_filter'] = DeviceFilter.parse(args[0])
        else:
            self._params['device_filter'] = \
                DeviceFilter(cls=cls, vendor=vendor, device=device)
        return self

    def with_parser(self, parser: Optional[Parser] = None) -> 'CommandBuilder':
        """
        Use a pylspci parser to get parsed Device instances instead of strings.

        :param parser: The parser to use. Set to None to disable parsing.
        :type parser: pylspci.parsers.Parser
        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        self._parser = parser
        return self

    def with_default_parser(self) -> 'CommandBuilder':
        """
        Use the default parser compatible with the current set of settings.
        Note that this should be used as one of the last instructions of the
        builder, as the default parser can change if the settings are updated.

        :returns: The current CommandBuilder instance.
        :rtype: CommandBuilder
        """
        if self._params.get('verbose'):
            from pylspci.parsers import VerboseParser
            return self.with_parser(VerboseParser())
        else:
            from pylspci.parsers import SimpleParser
            return self.with_parser(SimpleParser())
