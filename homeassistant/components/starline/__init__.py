"""The StarLine component."""

from __future__ import annotations

import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_SCAN_INTERVAL
from menuai.core import menuai, ServiceCall
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .account import StarlineAccount
from .const import (
    CONF_SCAN_OBD_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_OBD_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_SCAN_INTERVAL,
    SERVICE_SET_SCAN_OBD_INTERVAL,
    SERVICE_UPDATE_STATE,
)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the StarLine device from a config entry."""
    account = StarlineAccount(menuai, entry)
    await account.update()
    await account.update_obd()
    if not account.api.available:
        raise ConfigEntryNotReady

    if DOMAIN not in menuai.data:
        menuai.data[DOMAIN] = {}
    menuai.data[DOMAIN][entry.entry_id] = account

    device_registry = dr.async_get(menuai)
    for device in account.api.devices.values():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, **account.device_info(device)
        )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_set_scan_interval(call: ServiceCall) -> None:
        """Set scan interval."""
        options = dict(entry.options)
        options[CONF_SCAN_INTERVAL] = call.data[CONF_SCAN_INTERVAL]
        menuai.config_entries.async_update_entry(entry=entry, options=options)

    async def async_set_scan_obd_interval(call: ServiceCall) -> None:
        """Set OBD info scan interval."""
        options = dict(entry.options)
        options[CONF_SCAN_OBD_INTERVAL] = call.data[CONF_SCAN_INTERVAL]
        menuai.config_entries.async_update_entry(entry=entry, options=options)

    async def async_update(call: ServiceCall | None = None) -> None:
        """Update all data."""
        await account.update()
        await account.update_obd()

    menuai.services.async_register(DOMAIN, SERVICE_UPDATE_STATE, async_update)
    menuai.services.async_register(
        DOMAIN,
        SERVICE_SET_SCAN_INTERVAL,
        async_set_scan_interval,
        schema=vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=10)
                )
            }
        ),
    )
    menuai.services.async_register(
        DOMAIN,
        SERVICE_SET_SCAN_OBD_INTERVAL,
        async_set_scan_obd_interval,
        schema=vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=180)
                )
            }
        ),
    )

    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    await async_options_updated(menuai, entry)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    account: StarlineAccount = menuai.data[DOMAIN][config_entry.entry_id]
    account.unload()
    return unload_ok


async def async_options_updated(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Triggered by config entry options updates."""
    account: StarlineAccount = menuai.data[DOMAIN][config_entry.entry_id]
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_obd_interval = config_entry.options.get(
        CONF_SCAN_OBD_INTERVAL, DEFAULT_SCAN_OBD_INTERVAL
    )
    account.set_update_interval(scan_interval)
    account.set_update_obd_interval(scan_obd_interval)
