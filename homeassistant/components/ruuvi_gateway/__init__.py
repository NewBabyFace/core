"""The Ruuvi Gateway integration."""

from __future__ import annotations

import logging

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .bluetooth import async_connect_scanner
from .const import DOMAIN
from .coordinator import RuuviGatewayUpdateCoordinator
from .models import RuuviGatewayRuntimeData

_LOGGER = logging.getLogger(DOMAIN)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Ruuvi Gateway from a config entry."""
    coordinator = RuuviGatewayUpdateCoordinator(menuai, entry, _LOGGER)
    scanner, unload_scanner = async_connect_scanner(menuai, entry, coordinator)
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = RuuviGatewayRuntimeData(
        update_coordinator=coordinator,
        scanner=scanner,
    )
    entry.async_on_unload(unload_scanner)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, []):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
