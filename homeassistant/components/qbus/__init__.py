"""The Qbus integration."""

import logging

from menuai.components.mqtt import async_wait_for_mqtt_client
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import (
    QBUS_KEY,
    QbusConfigCoordinator,
    QbusConfigEntry,
    QbusControllerCoordinator,
)

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Qbus integration.

    We set up a single coordinator for managing Qbus config updates. The
    config update contains the configuration for all controllers (and
    config entries). This avoids having each device requesting and managing
    the config on its own.
    """
    _LOGGER.debug("Loading integration")

    if not await async_wait_for_mqtt_client(menuai):
        _LOGGER.error("MQTT integration not available")
        return False

    config_coordinator = QbusConfigCoordinator.get_or_create(menuai)
    await config_coordinator.async_subscribe_to_config()
    return True


async def async_setup_entry(menuai: menuai, entry: QbusConfigEntry) -> bool:
    """Set up Qbus from a config entry."""
    _LOGGER.debug("%s - Loading entry", entry.unique_id)

    if not await async_wait_for_mqtt_client(menuai):
        _LOGGER.error("MQTT integration not available")
        raise ConfigEntryNotReady("MQTT integration not available")

    coordinator = QbusControllerCoordinator(menuai, entry)
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Get current config
    config = await QbusConfigCoordinator.get_or_create(
        menuai
    ).async_get_or_request_config()

    # Update the controller config
    if config:
        await coordinator.async_update_controller_config(config)

    return True


async def async_unload_entry(menuai: menuai, entry: QbusConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("%s - Unloading entry", entry.unique_id)

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.shutdown()
        _cleanup(menuai, entry)

    return unload_ok


def _cleanup(menuai: menuai, entry: QbusConfigEntry) -> None:
    """Shutdown if no more entries are loaded."""
    if not menuai.config_entries.async_loaded_entries(DOMAIN) and (
        config_coordinator := menuai.data.get(QBUS_KEY)
    ):
        config_coordinator.shutdown()
