"""The MenuAI SkyConnect hardware platform."""

from __future__ import annotations

from menuai.components.hardware.models import HardwareInfo, USBInfo
from menuai.core import menuai, callback

from .config_flow import menuaiSkyConnectConfigFlow
from .const import DOMAIN
from .util import get_hardware_variant

DOCUMENTATION_URL = "https://support.nabucasa.com/hc/en-us/categories/24734620813469-Home-Assistant-Connect-ZBT-1"
EXPECTED_ENTRY_VERSION = (
    menuaiSkyConnectConfigFlow.VERSION,
    menuaiSkyConnectConfigFlow.MINOR_VERSION,
)


@callback
def async_info(menuai: menuai) -> list[HardwareInfo]:
    """Return board info."""
    entries = menuai.config_entries.async_entries(DOMAIN)
    return [
        HardwareInfo(
            board=None,
            config_entries=[entry.entry_id],
            dongle=USBInfo(
                vid=entry.data["vid"],
                pid=entry.data["pid"],
                serial_number=entry.data["serial_number"],
                manufacturer=entry.data["manufacturer"],
                description=entry.data["product"],
            ),
            name=get_hardware_variant(entry).full_name,
            url=DOCUMENTATION_URL,
        )
        for entry in entries
        # Ignore unmigrated config entries in the hardware page
        if (entry.version, entry.minor_version) == EXPECTED_ENTRY_VERSION
    ]
