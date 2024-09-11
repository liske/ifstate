import argparse
import shlex
from typing import Any, Iterable, List, Union

from cached_property import cached_property

from pylspci.device import Device
from pylspci.fields import NameWithID, Slot, hexstring
from pylspci.parsers.base import Parser


class SimpleParser(Parser):
    """
    A parser for lspci -mm.
    """

    @cached_property
    def _parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser()
        p.add_argument(
            'slot',
            type=Slot,
        )
        p.add_argument(
            'cls',
            type=NameWithID,
        )
        p.add_argument(
            'vendor',
            type=NameWithID,
        )
        p.add_argument(
            'device',
            type=NameWithID,
        )
        p.add_argument(
            'subsystem_vendor',
            type=NameWithID,
        )
        p.add_argument(
            'subsystem_device',
            type=NameWithID,
        )
        p.add_argument(
            '-r',
            type=hexstring,
            nargs='?',
            dest='revision',
        )
        p.add_argument(
            '-p',
            type=hexstring,
            nargs='?',
            dest='progif',
        )
        return p

    def parse(
            self,
            data: Union[str, Iterable[str], Iterable[Iterable[str]]],
            ) -> List[Device]:
        """
        Parse a multiline string or a list of single-line strings
        from lspci -mm into devices.

        :param data: A string holding multiple devices,
           a list of strings, one for each device,
           or a list of lists of strings, one list for each device, with
           each list holding each part of the device output.
        :type data: str or Iterable[str] or Iterable[Iterable[str]]
        :return: A list of parsed devices.
        :rtype: List[Device]
        """
        if isinstance(data, str):
            data = data.splitlines()
        return list(map(self.parse_line, data))

    def parse_line(self, args: Union[str, Iterable[str]]) -> Device:
        """
        Parse a single line from lspci -mm into a single device, either
        as the line or as a list of fields.

        :param args: Line or list of fields to parse from.
        :type args: str or Iterable[str]
        :return: A single parsed device.
        :rtype: Device
        """
        if isinstance(args, str):
            args = shlex.split(args)
        return Device(**vars(self._parser.parse_args(args)))

    def run(self, **kwargs: Any) -> List[Device]:
        if kwargs.get('verbose'):
            raise ValueError(
                'Verbose output is unsupported from the SimpleParser. '
                'Please use the pylspci.parsers.VerboseParser instead.'
            )
        return super().run(**kwargs)
