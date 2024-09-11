import warnings
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Union

from pylspci.device import Device
from pylspci.fields import NameWithID, Slot, hexstring
from pylspci.parsers.base import Parser

UNKNOWN_FIELD_WARNING = (
    'Unsupported device field {!r} with value {!r}\n'
    'Please report this, along with the output of `lspci -mmnnvvvk`, at '
    'https://tildegit.org/lucidiot/pylspci/issues/new'
)


class FieldMapping(NamedTuple):
    """
    Helper class to map verbose output field names such as ``SVendor`` to
    :class:`Device` fields such as ``subsytem_vendor``.
    """

    field_name: str
    """
    Field name on the :class:`Device` named tuple.
    """

    field_type: Callable[[str], Any]
    """
    Field type; a callable to use to parse the string value.
    """

    many: bool = False
    """
    Whether or not to use a List, if this field can be repeated multiple times
    in the lspci output.
    """


class VerboseParser(Parser):
    """
    A parser for lspci -vvvmmk
    """

    default_lspci_args = {
        'verbose': True,
        'kernel_drivers': True,
    }

    # Maps lspci output fields to Device fields with a type
    _field_mapping = {
        'Slot': FieldMapping(field_name='slot', field_type=Slot),
        'Class': FieldMapping(field_name='cls', field_type=NameWithID),
        'Vendor': FieldMapping(field_name='vendor', field_type=NameWithID),
        'Device': FieldMapping(field_name='device', field_type=NameWithID),
        'SVendor': FieldMapping(
            field_name='subsystem_vendor',
            field_type=NameWithID,
        ),
        'SDevice': FieldMapping(
            field_name='subsystem_device',
            field_type=NameWithID,
        ),
        'Rev': FieldMapping(field_name='revision', field_type=hexstring),
        'ProgIf': FieldMapping(field_name='progif', field_type=hexstring),
        'Driver': FieldMapping(field_name='driver', field_type=str),
        'Module': FieldMapping(
            field_name='kernel_modules',
            field_type=str,
            many=True,
        ),
        'NUMANode': FieldMapping(field_name='numa_node', field_type=int),
        'IOMMUGroup': FieldMapping(field_name='iommu_group', field_type=int),
        'PhySlot': FieldMapping(field_name='physical_slot', field_type=str),
    }

    def _parse_device(self, device_data: Union[str, Iterable[str]]) -> Device:
        devdict: Dict[str, Any] = {}
        if isinstance(device_data, str):
            device_data = device_data.splitlines()

        for line in device_data:
            key, _, value = map(str.strip, line.partition(':'))
            if key not in self._field_mapping:
                warnings.warn(
                    UNKNOWN_FIELD_WARNING.format(key, value),
                    UserWarning,
                )
                continue
            field = self._field_mapping[key]
            if field.many:
                devdict.setdefault(field.field_name, []) \
                       .append(field.field_type(value))
            else:
                devdict[field.field_name] = field.field_type(value)

        return Device(**devdict)

    def parse(
            self,
            data: Union[str, Iterable[str], Iterable[Iterable[str]]],
            ) -> List[Device]:
        """
        Parse an lspci -vvvmm[nnk] output, either as a single string holding
        multiple devices separated by two newlines,
        or as a list of multiline strings holding one device each.

        :param data: A string holding multiple devices,
           a list of strings, one for each device,
           or a list of lists of strings, one list for each device, with
           each list holding each part of the device output.
        :type data: str or Iterable[str] or Iterable[Iterable[str]]
        :return: A list of parsed devices.
        :rtype: List[Device]
        """
        if isinstance(data, str):
            data = data.split('\n\n')
        result: List[Device] = []
        for line in data:
            if isinstance(line, str):
                line = str.strip(line)
            if not line:  # Ignore empty strings and lists
                continue
            result.append(self._parse_device(line))
        return result
