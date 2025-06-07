"""Support for Kaiterra devices."""

import voluptuous as vol

from menuai.const import (
    CONF_API_KEY,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
)
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.discovery import async_load_platform
from menuai.helpers.event import async_track_time_interval
from menuai.helpers.typing import ConfigType

from .api_data import KaiterraApiData
from .const import (
    AVAILABLE_AQI_STANDARDS,
    AVAILABLE_DEVICE_TYPES,
    AVAILABLE_UNITS,
    CONF_AQI_STANDARD,
    CONF_PREFERRED_UNITS,
    DEFAULT_AQI_STANDARD,
    DEFAULT_PREFERRED_UNIT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

KAITERRA_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_TYPE): vol.In(AVAILABLE_DEVICE_TYPES),
        vol.Optional(CONF_NAME): cv.string,
    }
)

KAITERRA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [KAITERRA_DEVICE_SCHEMA]),
        vol.Optional(CONF_AQI_STANDARD, default=DEFAULT_AQI_STANDARD): vol.In(
            AVAILABLE_AQI_STANDARDS
        ),
        vol.Optional(CONF_PREFERRED_UNITS, default=DEFAULT_PREFERRED_UNIT): vol.All(
            cv.ensure_list, [vol.In(AVAILABLE_UNITS)]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: KAITERRA_SCHEMA}, extra=vol.ALLOW_EXTRA)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Kaiterra integration."""

    conf = config[DOMAIN]
    scan_interval = conf[CONF_SCAN_INTERVAL]
    devices = conf[CONF_DEVICES]
    session = async_get_clientsession(menuai)
    api = menuai.data[DOMAIN] = KaiterraApiData(menuai, conf, session)

    await api.async_update()

    async def _update(now=None):
        """Periodic update."""
        await api.async_update()

    async_track_time_interval(menuai, _update, scan_interval)

    # Load platforms for each device
    for device in devices:
        device_name, device_id = (
            device.get(CONF_NAME) or device[CONF_TYPE],
            device[CONF_DEVICE_ID],
        )
        for platform in PLATFORMS:
            menuai.async_create_task(
                async_load_platform(
                    menuai,
                    platform,
                    DOMAIN,
                    {CONF_NAME: device_name, CONF_DEVICE_ID: device_id},
                    config,
                )
            )

    return True
