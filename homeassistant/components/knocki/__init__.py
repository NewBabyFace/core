"""The Knocki integration."""

from __future__ import annotations

from knocki import Event, EventType, KnockiClient

from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import KnockiConfigEntry, KnockiCoordinator

PLATFORMS: list[Platform] = [Platform.EVENT]


async def async_setup_entry(menuai: menuai, entry: KnockiConfigEntry) -> bool:
    """Set up Knocki from a config entry."""
    client = KnockiClient(
        session=async_get_clientsession(menuai), token=entry.data[CONF_TOKEN]
    )

    coordinator = KnockiCoordinator(menuai, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(
        client.register_listener(EventType.CREATED, coordinator.add_trigger)
    )

    async def _refresh_coordinator(_: Event) -> None:
        await coordinator.async_refresh()

    entry.async_on_unload(
        client.register_listener(EventType.DELETED, _refresh_coordinator)
    )

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await client.start_websocket()

    return True


async def async_unload_entry(menuai: menuai, entry: KnockiConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.client.close()
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
