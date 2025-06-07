"""The WiLight integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .parent_device import WiLightParent

# List the platforms that you want to support.
PLATFORMS = [Platform.COVER, Platform.FAN, Platform.LIGHT, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a wilight config entry."""

    parent = WiLightParent(menuai, entry)

    if not await parent.async_setup():
        raise ConfigEntryNotReady

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = parent

    # Set up all platforms for this device/entry.
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload WiLight config entry."""

    # Unload entities for this entry/device.
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Cleanup
    parent = menuai.data[DOMAIN][entry.entry_id]
    await parent.async_reset()
    del menuai.data[DOMAIN][entry.entry_id]

    return unload_ok
