"""Vodafone Station integration."""

from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai

from .coordinator import VodafoneConfigEntry, VodafoneStationRouter
from .utils import async_client_session

PLATFORMS = [Platform.BUTTON, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: VodafoneConfigEntry) -> bool:
    """Set up Vodafone Station platform."""
    session = await async_client_session(menuai)
    coordinator = VodafoneStationRouter(
        menuai,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry,
        session,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: VodafoneConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = entry.runtime_data
        await coordinator.api.logout()
        await coordinator.api.close()

    return unload_ok


async def update_listener(menuai: menuai, entry: VodafoneConfigEntry) -> None:
    """Update when config_entry options update."""
    if entry.options:
        await menuai.config_entries.async_reload(entry.entry_id)
