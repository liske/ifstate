from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Union

from pylspci.device import Device


class Parser(ABC):

    default_lspci_args: Dict[str, Any] = {}
    """
    The default arguments that, when sent to :func:`lspci`, should provide the
    best output for this parser.

    See :func:`lspci`'s documentation for a list of available arguments.
    """

    @abstractmethod
    def parse(
            self,
            data: Union[str, Iterable[str], Iterable[Iterable[str]]]
            ) -> List[Device]:
        """
        Parse a string or list of strings as a list of devices.

        :param data: A string holding multiple devices,
           a list of strings, one for each device,
           or a list of lists of strings, one list for each device, with
           each list holding each part of the device output.
        :type data: str or Iterable[str] or Iterable[Iterable[str]]
        :returns: A list of parsed devices.
        :rtype: List[Device]
        """

    def run(self, **kwargs: Any) -> List[Device]:
        """
        Run the lspci command with the given arguments, defaulting to the
        parser's default arguments, and parse the result.

        :param \\**kwargs: Optional arguments to override the parser's default
           arguments. See :func:`lspci`'s documentation for a list of
           available arguments.
        :type \\**kwargs: Any
        :returns: A list of parsed devices.
        :rtype: List[Device]
        """
        from pylspci.command import lspci
        lspci_kwargs = self.default_lspci_args.copy()
        lspci_kwargs.update(kwargs)
        return self.parse(lspci(**lspci_kwargs))
