"""The JuiceNet integration."""

from datetime import timedelta
import logging

import aiohttp
from pyjuicenet import Api, TokenError
import voluptuous as vol

from menuai.config_entries import SOURCE_IMPORT, ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, JUICENET_API, JUICENET_COORDINATOR
from .device import JuiceNetApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {DOMAIN: vol.Schema({vol.Required(CONF_ACCESS_TOKEN): cv.string})},
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the JuiceNet component."""
    conf = config.get(DOMAIN)
    menuai.data.setdefault(DOMAIN, {})

    if not conf:
        return True

    menuai.async_create_task(
        menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up JuiceNet from a config entry."""

    config = entry.data

    session = async_get_clientsession(menuai)

    access_token = config[CONF_ACCESS_TOKEN]
    api = Api(access_token, session)

    juicenet = JuiceNetApi(api)

    try:
        await juicenet.setup()
    except TokenError as error:
        _LOGGER.error("JuiceNet Error %s", error)
        return False
    except aiohttp.ClientError as error:
        _LOGGER.error("Could not reach the JuiceNet API %s", error)
        raise ConfigEntryNotReady from error

    if not juicenet.devices:
        _LOGGER.error("No JuiceNet devices found for this account")
        return False
    _LOGGER.debug("%d JuiceNet device(s) found", len(juicenet.devices))

    async def async_update_data():
        """Update all device states from the JuiceNet API."""
        for device in juicenet.devices:
            await device.update_state(True)
        return True

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name="JuiceNet",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN][entry.entry_id] = {
        JUICENET_API: juicenet,
        JUICENET_COORDINATOR: coordinator,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
