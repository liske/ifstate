import re
from functools import partial
from typing import Any, Dict, Optional, Union

# mypy does not support recursive type definitions
# SlotDict = Dict[str, Union[int, 'SlotDict', None]]
SlotDict = Dict[str, Union[int, Dict[str, Any], None]]
NameWithIDDict = Dict[str, Union[int, str, None]]

hexstring = partial(int, base=16)


class Slot(object):
    """
    Describes a PCI slot identifier, in the format ``[DDDD:]BB:dd.f``,
    where ``D`` is the domain, ``B`` the bus, ``d`` the device
    and ``f`` the function. The first three are hexadecimal numbers, but
    ``f`` is in octal.
    """

    domain: int = 0x0000
    """
    The slot's domain, as a four-digit hexadecimal number.
    When omitted, defaults to ``0x0000``.
    """

    bus: int
    """
    The slot's bus, as a two-digit hexadecimal number.
    """

    device: int
    """
    The slot's device, as a two-digit hexadecimal number, up to `0x1f`.
    """

    function: int
    """
    The slot's function, as a single octal digit.
    """

    parent: Optional["Slot"] = None
    """
    The slot's parent bridge, if present.
    """

    def __init__(self, value: str) -> None:
        parent, _, me = value.rpartition('/')
        if parent:
            self.parent = Slot(parent)

        data = list(map(hexstring, re.split(r'[:\.]', me)))
        if len(data) == 3:
            data.insert(0, self.parent.domain if self.parent else 0)
        self.domain, self.bus, self.device, self.function = data

        if self.device > 0x1f:
            raise ValueError('Device numbers cannot be above 0x1f')
        if self.function > 0x7:
            raise ValueError('Function numbers cannot be above 7')

    def __str__(self) -> str:
        output: str = '{:04x}:{:02x}:{:02x}.{:01x}'.format(
            self.domain, self.bus, self.device, self.function,
        )
        if self.parent:
            return '{!s}/{}'.format(self.parent, output)
        return output

    def __repr__(self) -> str:
        return '{}({!r})'.format(self.__class__.__name__, str(self))

    def as_dict(self) -> SlotDict:
        """
        Serialize this slot as a JSON-serializable `dict`.
        """
        return {
            "domain": self.domain,
            "bus": self.bus,
            "device": self.device,
            "function": self.function,
            "parent": self.parent.as_dict() if self.parent else None,
        }


class NameWithID(object):
    """
    Describes a device, vendor or class with either
    a name, an hexadecimal PCI ID, or both.
    """

    id: Optional[int]
    """
    The PCI ID as a four-digit hexadecimal number.
    """

    name: Optional[str]
    """
    The human-readable name associated with this ID.
    """

    _NAME_ID_REGEX = re.compile(r'^(?P<name>.+)\s\[(?P<id>[0-9a-fA-F]{4})\]$')

    def __init__(self, value: Optional[str]) -> None:
        if value and value.endswith(']'):
            # Holds both an ID and a name
            match = self._NAME_ID_REGEX.match(value)
            if not match:  # Except it doesn't
                self.id = None
                self.name = value
                return
            gd = match.groupdict()
            self.id = hexstring(gd['id'])
            self.name = gd['name']
            return

        try:
            self.id = hexstring(value)
            self.name = None
        except (TypeError, ValueError):
            self.id = None
            self.name = value

    def __str__(self) -> str:
        if self.id and self.name:
            return '{} [{:04x}]'.format(self.name, self.id)
        elif self.name:
            return self.name
        elif self.id:
            return '{:04x}'.format(self.id)
        else:
            return ''

    def __repr__(self) -> str:
        return '{}({!r})'.format(self.__class__.__name__, str(self))

    def as_dict(self) -> NameWithIDDict:
        """
        Serialize this name and ID as a JSON-serializable `dict`.
        """
        return {
            "id": self.id,
            "name": self.name,
        }


class PCIAccessParameter(object):
    """
    A pcilib access method parameter, as parsed from :func:`list_pcilib_params`
    or ``lspci -Ohelp``, that can be modified using the ``pcilib_params``
    argument of :func:`lspci`, or ``lspci -Oname=value`` in the command line.
    """

    name: str
    """
    The parameter's name.
    """

    description: str
    """
    A short description of the parameter's use.
    """

    default: Optional[str]
    """
    An optional default value for the parameter.
    """

    _PARAM_REGEX = re.compile(
        r'^(?P<name>\S+)\s+(?P<description>.+)\s\((?P<default>.*)\)$')

    def __init__(self, value: str) -> None:
        match = self._PARAM_REGEX.match(value)
        if not match:
            raise ValueError(
                'Could not parse {!r} into a parameter'.format(value))
        gd = match.groupdict()
        self.name = gd['name'].strip()
        self.description = gd['description'].strip()
        self.default = gd['default'].strip() or None

    def __str__(self) -> str:
        return '{}\t{} ({})'.format(self.name, self.description, self.default)

    def __repr__(self) -> str:
        return '{!s}({!r})'.format(self.__class__.__name__, str(self))

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, PCIAccessParameter) and \
            (self.name, self.description, self.default) \
            == (other.name, other.description, other.default)

    def as_dict(self) -> Dict[str, Optional[str]]:
        """
        Serialize this PCI access parameter as a JSON-serializable `dict`.
        """
        return {
            "name": self.name,
            "description": self.description,
            "default": self.default,
        }
