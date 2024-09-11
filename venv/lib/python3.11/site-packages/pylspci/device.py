from typing import Dict, List, NamedTuple, Optional, Union

from pylspci.fields import NameWithID, NameWithIDDict, Slot, SlotDict

DeviceDict = Dict[str, Union[
    int,
    str,
    SlotDict,
    NameWithIDDict,
    List[str],
    None,
]]


class Device(NamedTuple):
    """
    Describes a device returned by lspci.
    """

    slot: Slot
    """
    The device's slot (domain, bus, number and function).
    """

    cls: NameWithID
    """
    The device's class, with a name and/or an ID.
    """

    vendor: NameWithID
    """
    The device's vendor, with a name and/or an ID.
    """

    device: NameWithID
    """
    The device's name and/or ID.
    """

    subsystem_vendor: Optional[NameWithID] = None
    """
    The device's subsystem vendor, if found, with a name and/or an ID.
    """

    subsystem_device: Optional[NameWithID] = None
    """
    The device's subsystem name and/or ID, if found.
    """

    revision: Optional[int] = None
    """
    The device's revision number.
    """

    progif: Optional[int] = None
    """
    The device's programming interface number.
    """

    driver: Optional[str] = None
    """
    The device's driver (Linux only).
    """

    kernel_modules: List[str] = []
    """
    One or more kernel modules that can handle this device (Linux only).
    """

    numa_node: Optional[int] = None
    """
    NUMA node this device is connected to (Linux only).
    """

    iommu_group: Optional[int] = None
    """
    IOMMU group that this device is part of (optional, Linux only).
    """

    physical_slot: Optional[str] = None
    """
    The device's physical slot number (Linux only).
    """

    def as_dict(self) -> DeviceDict:
        """
        Serialize this device as a JSON-serializable `dict`.
        """
        return {
            "slot": self.slot.as_dict(),
            "cls": self.cls.as_dict(),
            "vendor": self.vendor.as_dict(),
            "device": self.device.as_dict(),
            "subsystem_vendor": (
                self.subsystem_vendor.as_dict()
                if self.subsystem_vendor
                else None
            ),
            "subsystem_device": (
                self.subsystem_device.as_dict()
                if self.subsystem_device
                else None
            ),
            "revision": self.revision,
            "progif": self.progif,
            "driver": self.driver,
            "kernel_modules": self.kernel_modules,
            "numa_node": self.numa_node,
            "iommu_group": self.iommu_group,
            "physical_slot": self.physical_slot,
        }
