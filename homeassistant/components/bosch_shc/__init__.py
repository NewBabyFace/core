"""The Bosch Smart Home Controller integration."""

import logging

from boschshcpy import SHCSession
from boschshcpy.exceptions import SHCAuthenticationError, SHCConnectionError

from menuai.components.zeroconf import async_get_instance
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, EVENT_menuai_STOP, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .const import CONF_SSL_CERTIFICATE, CONF_SSL_KEY, DOMAIN

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


type BoschConfigEntry = ConfigEntry[SHCSession]


async def async_setup_entry(menuai: menuai, entry: BoschConfigEntry) -> bool:
    """Set up Bosch SHC from a config entry."""
    data = entry.data

    zeroconf = await async_get_instance(menuai)
    try:
        session = await menuai.async_add_executor_job(
            SHCSession,
            data[CONF_HOST],
            data[CONF_SSL_CERTIFICATE],
            data[CONF_SSL_KEY],
            False,
            zeroconf,
        )
    except SHCAuthenticationError as err:
        raise ConfigEntryAuthFailed from err
    except SHCConnectionError as err:
        raise ConfigEntryNotReady from err

    shc_info = session.information
    if shc_info.updateState.name == "UPDATE_AVAILABLE":
        _LOGGER.warning("Please check for software updates in the Bosch Smart Home App")

    entry.runtime_data = session

    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, dr.format_mac(shc_info.unique_id))},
        identifiers={(DOMAIN, shc_info.unique_id)},
        manufacturer="Bosch",
        name=entry.title,
        model="SmartHomeController",
        sw_version=shc_info.version,
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def stop_polling(event):
        """Stop polling service."""
        await menuai.async_add_executor_job(session.stop_polling)

    await menuai.async_add_executor_job(session.start_polling)
    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, stop_polling)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: BoschConfigEntry) -> bool:
    """Unload a config entry."""
    await menuai.async_add_executor_job(entry.runtime_data.stop_polling)

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
