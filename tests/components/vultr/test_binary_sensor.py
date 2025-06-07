"""Test the Vultr binary sensor platform."""

import pytest
import voluptuous as vol

from menuai.components import vultr as base_vultr
from menuai.components.vultr import (
    ATTR_ALLOWED_BANDWIDTH,
    ATTR_AUTO_BACKUPS,
    ATTR_COST_PER_MONTH,
    ATTR_CREATED_AT,
    ATTR_IPV4_ADDRESS,
    ATTR_SUBSCRIPTION_ID,
    CONF_SUBSCRIPTION,
    binary_sensor as vultr,
)
from menuai.const import CONF_NAME, CONF_PLATFORM
from menuai.core import menuai

CONFIGS = [
    {CONF_SUBSCRIPTION: "576965", CONF_NAME: "A Server"},
    {CONF_SUBSCRIPTION: "123456", CONF_NAME: "Failed Server"},
    {CONF_SUBSCRIPTION: "555555", CONF_NAME: vultr.DEFAULT_NAME},
]


@pytest.mark.usefixtures("valid_config")
def test_binary_sensor(menuai: menuai) -> None:
    """Test successful instance."""
    menuai_devices = []

    def add_entities(devices, action):
        """Mock add devices."""
        for device in devices:
            device.menuai = menuai
            menuai_devices.append(device)

    # Setup each of our test configs
    for config in CONFIGS:
        vultr.setup_platform(menuai, config, add_entities, None)

    assert len(menuai_devices) == 3

    for device in menuai_devices:
        # Test pre data retrieval
        if device.subscription == "555555":
            assert device.name == "Vultr {}"

        device.update()
        device_attrs = device.extra_state_attributes

        if device.subscription == "555555":
            assert device.name == "Vultr Another Server"

        if device.name == "A Server":
            assert device.is_on is True
            assert device.device_class == "power"
            assert device.state == "on"
            assert device.icon == "mdi:server"
            assert device_attrs[ATTR_ALLOWED_BANDWIDTH] == "1000"
            assert device_attrs[ATTR_AUTO_BACKUPS] == "yes"
            assert device_attrs[ATTR_IPV4_ADDRESS] == "123.123.123.123"
            assert device_attrs[ATTR_COST_PER_MONTH] == "10.05"
            assert device_attrs[ATTR_CREATED_AT] == "2013-12-19 14:45:41"
            assert device_attrs[ATTR_SUBSCRIPTION_ID] == "576965"
        elif device.name == "Failed Server":
            assert device.is_on is False
            assert device.state == "off"
            assert device.icon == "mdi:server-off"
            assert device_attrs[ATTR_ALLOWED_BANDWIDTH] == "1000"
            assert device_attrs[ATTR_AUTO_BACKUPS] == "no"
            assert device_attrs[ATTR_IPV4_ADDRESS] == "192.168.100.50"
            assert device_attrs[ATTR_COST_PER_MONTH] == "73.25"
            assert device_attrs[ATTR_CREATED_AT] == "2014-10-13 14:45:41"
            assert device_attrs[ATTR_SUBSCRIPTION_ID] == "123456"


def test_invalid_sensor_config() -> None:
    """Test config type failures."""
    with pytest.raises(vol.Invalid):  # No subs
        vultr.PLATFORM_SCHEMA({CONF_PLATFORM: base_vultr.DOMAIN})


@pytest.mark.usefixtures("valid_config")
def test_invalid_sensors(menuai: menuai) -> None:
    """Test the VultrBinarySensor fails."""
    menuai_devices = []

    def add_entities(devices, action):
        """Mock add devices."""
        for device in devices:
            device.menuai = menuai
            menuai_devices.append(device)

    bad_conf = {}  # No subscription

    vultr.setup_platform(menuai, bad_conf, add_entities, None)

    bad_conf = {
        CONF_NAME: "Missing Server",
        CONF_SUBSCRIPTION: "555555",
    }  # Sub not associated with API key (not in server_list)

    vultr.setup_platform(menuai, bad_conf, add_entities, None)
