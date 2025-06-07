"""The lg_netcast component."""

from typing import Final

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv

from .const import DOMAIN

PLATFORMS: Final[list[Platform]] = [Platform.MEDIA_PLAYER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    menuai.data.setdefault(DOMAIN, {})

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        del menuai.data[DOMAIN][entry.entry_id]

    return unload_ok
