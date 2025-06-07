"""The Ollama integration."""

from __future__ import annotations

import asyncio
import logging

import httpx
import ollama

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_URL, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.util.ssl import get_default_context

from .const import (
    CONF_KEEP_ALIVE,
    CONF_MAX_HISTORY,
    CONF_MODEL,
    CONF_NUM_CTX,
    CONF_PROMPT,
    CONF_THINK,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "CONF_KEEP_ALIVE",
    "CONF_MAX_HISTORY",
    "CONF_MODEL",
    "CONF_NUM_CTX",
    "CONF_PROMPT",
    "CONF_THINK",
    "CONF_URL",
    "DOMAIN",
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = (Platform.CONVERSATION,)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Ollama from a config entry."""
    settings = {**entry.data, **entry.options}
    client = ollama.AsyncClient(host=settings[CONF_URL], verify=get_default_context())
    try:
        async with asyncio.timeout(DEFAULT_TIMEOUT):
            await client.list()
    except (TimeoutError, httpx.ConnectError) as err:
        raise ConfigEntryNotReady(err) from err

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload Ollama."""
    if not await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    menuai.data[DOMAIN].pop(entry.entry_id)
    return True
