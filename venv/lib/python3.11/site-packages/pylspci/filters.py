import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Pattern, Type, TypeVar

from pylspci.fields import hexstring

T = TypeVar('T', bound='Filter')


class Filter(ABC):

    _REGEX: ClassVar[Pattern]

    @classmethod
    def parse(cls: Type[T], value: str) -> T:
        if not value:
            return cls()
        match = cls._REGEX.match(value)
        data: Dict[str, str] = {}
        if match:
            data = {k: v for k, v in match.groupdict().items()
                    if v is not None}
        if not match or not data:
            raise ValueError('Value is not a valid filter string')
        return cls(**{
            k: hexstring(v)
            for k, v in data.items()
            if v != '' and v != '*'
        })

    @abstractmethod
    def __init__(self, **kwargs: Any) -> None:
        "Create a filter."


class SlotFilter(Filter):
    """
    Describes a slot filter, to filter devices geographically.

    Any field set to ``None`` will remove filtering.
    """

    domain: Optional[int] = None
    """
    Device domain, as a four-digit hexadecimal number.
    """

    bus: Optional[int] = None
    """
    Device bus, as a two-digit hexadecimal number.
    """

    device: Optional[int] = None
    """
    Device number, as a two-digit hexadecimal number, up to `0x1f`.
    """

    function: Optional[int] = None
    """
    The slot's function, as a single octal digit.
    """

    # [[domain:]bus:][device][.function]
    _REGEX: ClassVar[Pattern] = re.compile(
        r'^(?:(?:(?P<domain>(?:[0-9a-f]{1,4}|\*?)):)?'
        r'(?P<bus>(?:[0-9a-f]{1,2}|\*?)):)?'
        r'(?P<device>(?:[01]?[0-9a-f]|\*?))?'
        r'(?:\.(?P<function>(?:[0-7]|\*?)))?$'
    )

    def __init__(self, *,
                 domain: Optional[int] = None,
                 bus: Optional[int] = None,
                 device: Optional[int] = None,
                 function: Optional[int] = None,
                 ):
        self.domain = domain
        self.bus = bus
        self.device = device
        self.function = function

    def __repr__(self) -> str:
        return '{}(domain={!r}, bus={!r}, device={!r}, function={!r})'.format(
            self.__class__.__name__,
            self.domain, self.bus, self.device, self.function,
        )

    def __str__(self) -> str:
        return '{}:{}:{}.{}'.format(*map(
            lambda x: '{:x}'.format(x) if x is not None else '',
            (self.domain, self.bus, self.device, self.function),
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.domain, self.bus, self.device, self.function) == \
            (other.domain, other.bus, other.device, other.function)


class DeviceFilter(Filter):
    """
    Describes a device filter, to filter devices logically.

    Any field set to ``None`` will remove filtering.
    """

    cls: Optional[int] = None
    """
    Device class ID, as a four-digit hexadecimal number.
    """

    vendor: Optional[int] = None
    """
    Device vendor ID, as a four-digit hexadecimal number.
    """

    device: Optional[int] = None
    """
    Device ID, as a four-digit hexadecimal number.
    """

    # [vendor]:[device][:class]
    _REGEX: ClassVar[Pattern] = re.compile(
        r'^(?P<vendor>(?:[0-9a-f]{1,4}|\*?)):'
        r'(?P<device>(?:[0-9a-f]{1,4}|\*?))'
        r'(?::(?P<cls>(?:[0-9a-f]{1,4}|\*?))?)?$'
    )

    def __init__(self, *,
                 cls: Optional[int] = None,
                 vendor: Optional[int] = None,
                 device: Optional[int] = None,
                 ):
        self.cls = cls
        self.vendor = vendor
        self.device = device

    def __repr__(self) -> str:
        return '{}(cls={!r}, vendor={!r}, device={!r})'.format(
            self.__class__.__name__, self.cls, self.vendor, self.device,
        )

    def __str__(self) -> str:
        return ':'.join(map(
            lambda x: '{:x}'.format(x) if x is not None else '',
            (self.vendor, self.device, self.cls),
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.vendor, self.device, self.cls) == \
            (other.vendor, other.device, other.cls)
