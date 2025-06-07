"""Support for Soma Smartshades."""

from __future__ import annotations

from api.soma_api import SomaApi
import voluptuous as vol

from menuai import config_entries
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import API, DEVICES, DOMAIN, HOST, PORT

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {
            DOMAIN: vol.Schema(
                {vol.Required(CONF_HOST): cv.string, vol.Required(CONF_PORT): cv.string}
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.COVER, Platform.SENSOR]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Soma component."""
    if DOMAIN not in config:
        return True

    menuai.async_create_task(
        menuai.config_entries.flow.async_init(
            DOMAIN,
            data=config[DOMAIN],
            context={"source": config_entries.SOURCE_IMPORT},
        )
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Soma from a config entry."""
    menuai.data[DOMAIN] = {}
    api = await menuai.async_add_executor_job(SomaApi, entry.data[HOST], entry.data[PORT])
    devices = await menuai.async_add_executor_job(api.list_devices)
    menuai.data[DOMAIN] = {API: api, DEVICES: devices["shades"]}

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
