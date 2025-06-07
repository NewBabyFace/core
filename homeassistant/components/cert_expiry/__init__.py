"""The cert_expiry component."""

from __future__ import annotations

from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.helpers.start import async_at_started

from .coordinator import CertExpiryConfigEntry, CertExpiryDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: CertExpiryConfigEntry) -> bool:
    """Load the saved entities."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]

    coordinator = CertExpiryDataUpdateCoordinator(menuai, entry, host, port)

    entry.runtime_data = coordinator

    if entry.unique_id is None:
        menuai.config_entries.async_update_entry(entry, unique_id=f"{host}:{port}")

    async def _async_finish_startup(_: menuai) -> None:
        await coordinator.async_refresh()
        await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async_at_started(menuai, _async_finish_startup)
    return True


async def async_unload_entry(menuai: menuai, entry: CertExpiryConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
