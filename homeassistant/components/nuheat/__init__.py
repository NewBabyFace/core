"""Support for NuHeat thermostats."""

from datetime import timedelta
from http import HTTPStatus
import logging

import nuheat
import requests

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_SERIAL_NUMBER, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


def _get_thermostat(api, serial_number):
    """Authenticate and create the thermostat object."""
    api.authenticate()
    return api.get_thermostat(serial_number)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up NuHeat from a config entry."""

    conf = entry.data

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]
    serial_number = conf[CONF_SERIAL_NUMBER]

    api = nuheat.NuHeat(username, password)

    try:
        thermostat = await menuai.async_add_executor_job(
            _get_thermostat, api, serial_number
        )
    except requests.exceptions.Timeout as ex:
        raise ConfigEntryNotReady from ex
    except requests.exceptions.HTTPError as ex:
        if (
            ex.response.status_code > HTTPStatus.BAD_REQUEST
            and ex.response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR
        ):
            _LOGGER.error("Failed to login to nuheat: %s", ex)
            return False
        raise ConfigEntryNotReady from ex
    except Exception as ex:  # noqa: BLE001
        _LOGGER.error("Failed to login to nuheat: %s", ex)
        return False

    async def _async_update_data():
        """Fetch data from API endpoint."""
        await menuai.async_add_executor_job(thermostat.get_data)

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name=f"nuheat {serial_number}",
        update_method=_async_update_data,
        update_interval=timedelta(minutes=5),
    )

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = (thermostat, coordinator)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
