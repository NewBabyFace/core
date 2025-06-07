"""USB discovery data."""

from dataclasses import dataclass

from menuai.data_entry_flow import BaseServiceInfo


@dataclass(slots=True)
class UsbServiceInfo(BaseServiceInfo):
    """Prepared info from usb entries."""

    device: str
    vid: str
    pid: str
    serial_number: str | None
    manufacturer: str | None
    description: str | None
