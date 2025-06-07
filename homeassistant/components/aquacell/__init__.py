"""The Aquacell integration."""

from __future__ import annotations

from aioaquacell import AquacellApi
from aioaquacell.const import Brand

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BRAND
from .coordinator import AquacellConfigEntry, AquacellCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: AquacellConfigEntry) -> bool:
    """Set up Aquacell from a config entry."""
    session = async_get_clientsession(menuai)

    brand = entry.data.get(CONF_BRAND, Brand.AQUACELL)

    aquacell_api = AquacellApi(session, brand)

    coordinator = AquacellCoordinator(menuai, entry, aquacell_api)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AquacellConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
