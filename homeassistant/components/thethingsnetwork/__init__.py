"""Support for The Things network."""

import logging

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_HOST
from menuai.core import menuai

from .const import DOMAIN, PLATFORMS, TTN_API_HOST
from .coordinator import TTNCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Establish connection with The Things Network."""

    _LOGGER.debug(
        "Set up %s at %s",
        entry.data[CONF_API_KEY],
        entry.data.get(CONF_HOST, TTN_API_HOST),
    )

    coordinator = TTNCoordinator(menuai, entry)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.debug(
        "Remove %s at %s",
        entry.data[CONF_API_KEY],
        entry.data.get(CONF_HOST, TTN_API_HOST),
    )

    # Unload entities created for each supported platform
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del menuai.data[DOMAIN][entry.entry_id]
    return True
