"""Support for VersaSense MicroPnP devices."""

import logging

import pyversasense as pyv
import voluptuous as vol

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client, config_validation as cv
from menuai.helpers.discovery import async_load_platform
from menuai.helpers.typing import ConfigType

from .const import (
    KEY_CONSUMER,
    KEY_IDENTIFIER,
    KEY_MEASUREMENT,
    KEY_PARENT_MAC,
    KEY_PARENT_NAME,
    KEY_UNIT,
    PERIPHERAL_CLASS_SENSOR,
    PERIPHERAL_CLASS_SENSOR_ACTUATOR,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "versasense"

# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_HOST): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the versasense component."""
    session = aiohttp_client.async_get_clientsession(menuai)
    consumer = pyv.Consumer(config[DOMAIN]["host"], session)

    menuai.data[DOMAIN] = {KEY_CONSUMER: consumer}

    await _configure_entities(menuai, config, consumer)

    # Return boolean to indicate that initialization was successful.
    return True


async def _configure_entities(menuai, config, consumer):
    """Fetch all devices with their peripherals for representation."""
    devices = await consumer.fetchDevices()
    _LOGGER.debug(devices)

    sensor_info = {}
    switch_info = {}

    for mac, device in devices.items():
        _LOGGER.debug("Device connected: %s %s", device.name, mac)
        menuai.data[DOMAIN][mac] = {}

        for peripheral_id, peripheral in device.peripherals.items():
            menuai.data[DOMAIN][mac][peripheral_id] = peripheral

            if peripheral.classification == PERIPHERAL_CLASS_SENSOR:
                sensor_info = _add_entity_info(peripheral, device, sensor_info)
            elif peripheral.classification == PERIPHERAL_CLASS_SENSOR_ACTUATOR:
                switch_info = _add_entity_info(peripheral, device, switch_info)

    if sensor_info:
        _load_platform(menuai, config, Platform.SENSOR, sensor_info)

    if switch_info:
        _load_platform(menuai, config, Platform.SWITCH, switch_info)


def _add_entity_info(peripheral, device, entity_dict) -> None:
    """Add info from a peripheral to specified list."""
    for measurement in peripheral.measurements:
        entity_info = {
            KEY_IDENTIFIER: peripheral.identifier,
            KEY_UNIT: measurement.unit,
            KEY_MEASUREMENT: measurement.name,
            KEY_PARENT_NAME: device.name,
            KEY_PARENT_MAC: device.mac,
        }

        key = f"{entity_info[KEY_PARENT_MAC]}/{entity_info[KEY_IDENTIFIER]}/{entity_info[KEY_MEASUREMENT]}"
        entity_dict[key] = entity_info

    return entity_dict


def _load_platform(menuai, config, entity_type, entity_info):
    """Load platform with list of entity info."""
    menuai.async_create_task(
        async_load_platform(menuai, entity_type, DOMAIN, entity_info, config)
    )
