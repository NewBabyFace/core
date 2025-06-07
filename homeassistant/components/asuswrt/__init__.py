"""Support for ASUSWRT devices."""

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai

from .router import AsusWrtRouter

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]

type AsusWrtConfigEntry = ConfigEntry[AsusWrtRouter]


async def async_setup_entry(menuai: menuai, entry: AsusWrtConfigEntry) -> bool:
    """Set up AsusWrt platform."""

    router = AsusWrtRouter(menuai, entry)
    await router.setup()

    router.async_on_close(entry.add_update_listener(update_listener))

    async def async_close_connection(event: Event) -> None:
        """Close AsusWrt connection on HA Stop."""
        await router.close()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, async_close_connection)
    )

    entry.runtime_data = router

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AsusWrtConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        router = entry.runtime_data
        await router.close()

    return unload_ok


async def update_listener(menuai: menuai, entry: AsusWrtConfigEntry) -> None:
    """Update when config_entry options update."""
    router = entry.runtime_data

    if router.update_options(entry.options):
        await menuai.config_entries.async_reload(entry.entry_id)
