"""The Glances component."""

import logging
from typing import Any

from glances_api import Glances
from glances_api.exceptions import (
    GlancesApiAuthorizationError,
    GlancesApiError,
    GlancesApiNoDataAvailable,
)

from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    menuaiError,
)
from menuai.helpers.httpx_client import get_async_client

from .coordinator import GlancesConfigEntry, GlancesDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    menuai: menuai, config_entry: GlancesConfigEntry
) -> bool:
    """Set up Glances from config entry."""
    try:
        api = await get_api(menuai, dict(config_entry.data))
    except GlancesApiAuthorizationError as err:
        raise ConfigEntryAuthFailed from err
    except GlancesApiError as err:
        raise ConfigEntryNotReady from err
    except ServerVersionMismatch as err:
        raise ConfigEntryError(err) from err
    coordinator = GlancesDataUpdateCoordinator(menuai, config_entry, api)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: GlancesConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def get_api(menuai: menuai, entry_data: dict[str, Any]) -> Glances:
    """Return the api from glances_api."""
    httpx_client = get_async_client(menuai, verify_ssl=entry_data[CONF_VERIFY_SSL])
    for version in (4, 3):
        api = Glances(
            host=entry_data[CONF_HOST],
            port=entry_data[CONF_PORT],
            version=version,
            ssl=entry_data[CONF_SSL],
            username=entry_data.get(CONF_USERNAME),
            password=entry_data.get(CONF_PASSWORD),
            httpx_client=httpx_client,
        )
        try:
            await api.get_ha_sensor_data()
        except GlancesApiNoDataAvailable as err:
            _LOGGER.debug("Failed to connect to Glances API v%s: %s", version, err)
            continue
        _LOGGER.debug("Connected to Glances API v%s", version)
        return api
    raise ServerVersionMismatch("Could not connect to Glances API version 3 or 4")


class ServerVersionMismatch(menuaiError):
    """Raise exception if we fail to connect to Glances API."""
