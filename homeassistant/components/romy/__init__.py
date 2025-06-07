"""ROMY Integration."""

import romy

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD
from menuai.core import menuai

from .const import DOMAIN, LOGGER, PLATFORMS
from .coordinator import RomyVacuumCoordinator


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Initialize the ROMY platform via config entry."""

    new_romy = await romy.create_romy(
        config_entry.data[CONF_HOST], config_entry.data.get(CONF_PASSWORD, "")
    )

    coordinator = RomyVacuumCoordinator(menuai, config_entry, new_romy)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    LOGGER.debug("update_listener")
    await menuai.config_entries.async_reload(config_entry.entry_id)
