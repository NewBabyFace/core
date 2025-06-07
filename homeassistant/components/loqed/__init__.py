"""The loqed integration."""

from __future__ import annotations

import logging
import re

import aiohttp
from loqedAPI import loqed

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import LoqedDataCoordinator

PLATFORMS: list[str] = [Platform.LOCK, Platform.SENSOR]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up loqed from a config entry."""
    websession = async_get_clientsession(menuai)
    host = entry.data["bridge_ip"]
    apiclient = loqed.APIClient(websession, f"http://{host}")
    api = loqed.LoqedAPI(apiclient)

    try:
        lock = await api.async_get_lock(
            entry.data["lock_key_key"],
            entry.data["bridge_key"],
            int(entry.data["lock_key_local_id"]),
            re.sub(
                r"LOQED-([a-f0-9]+)\.local", r"\1", entry.data["bridge_mdns_hostname"]
            ),
        )
    except (
        TimeoutError,
        aiohttp.ClientError,
    ) as ex:
        raise ConfigEntryNotReady(f"Unable to connect to bridge at {host}") from ex
    coordinator = LoqedDataCoordinator(menuai, entry, api, lock)
    await coordinator.ensure_webhooks()

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: LoqedDataCoordinator = menuai.data[DOMAIN][entry.entry_id]

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    await coordinator.remove_webhooks()

    return unload_ok
