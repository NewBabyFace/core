"""Energenie Power-Sockets (EGPS) integration."""

from pyegps import PowerStripUSB, get_device
from pyegps.exceptions import MissingLibrary, UsbError

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import CONF_DEVICE_API_ID

PLATFORMS = [Platform.SWITCH]

type EnergenieConfigEntry = ConfigEntry[PowerStripUSB]


async def async_setup_entry(menuai: menuai, entry: EnergenieConfigEntry) -> bool:
    """Set up Energenie Power Sockets."""
    try:
        powerstrip: PowerStripUSB | None = get_device(entry.data[CONF_DEVICE_API_ID])

    except (MissingLibrary, UsbError) as ex:
        raise ConfigEntryError("Can't access usb devices.") from ex

    if powerstrip is None:
        raise ConfigEntryNotReady(
            "Can't access Energenie Power Sockets, will retry later."
        )

    entry.runtime_data = powerstrip
    entry.async_on_unload(powerstrip.release)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: EnergenieConfigEntry) -> bool:
    """Unload config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
