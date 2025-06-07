"""The Ecowitt Weather Station Component."""

from __future__ import annotations

from aioecowitt import EcoWittListener
from aiohttp import web

from menuai.components import webhook
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_WEBHOOK_ID, EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai, callback

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type EcowittConfigEntry = ConfigEntry[EcoWittListener]


async def async_setup_entry(menuai: menuai, entry: EcowittConfigEntry) -> bool:
    """Set up the Ecowitt component from UI."""
    ecowitt = entry.runtime_data = EcoWittListener()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_webhook(
        menuai: menuai, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle webhook callback."""
        return await ecowitt.handler(request)

    webhook.async_register(
        menuai, DOMAIN, entry.title, entry.data[CONF_WEBHOOK_ID], handle_webhook
    )

    @callback
    def _stop_ecowitt(_: Event) -> None:
        """Stop the Ecowitt listener."""
        webhook.async_unregister(menuai, entry.data[CONF_WEBHOOK_ID])

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, _stop_ecowitt)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: EcowittConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(menuai, entry.data[CONF_WEBHOOK_ID])

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
