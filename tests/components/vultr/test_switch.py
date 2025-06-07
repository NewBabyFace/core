"""Test the Vultr switch platform."""

from __future__ import annotations

import json
from unittest.mock import patch

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
    switch as vultr,
)
from menuai.const import CONF_NAME, CONF_PLATFORM
from menuai.core import menuai

from tests.common import load_fixture

CONFIGS = [
    {CONF_SUBSCRIPTION: "576965", CONF_NAME: "A Server"},
    {CONF_SUBSCRIPTION: "123456", CONF_NAME: "Failed Server"},
    {CONF_SUBSCRIPTION: "555555", CONF_NAME: vultr.DEFAULT_NAME},
]


@pytest.fixture(name="menuai_devices")
def load_menuai_devices(menuai: menuai):
    """Load a valid config."""
    menuai_devices = []

    def add_entities(devices, action):
        """Mock add devices."""
        for device in devices:
            device.menuai = menuai
            menuai_devices.append(device)

    # Setup each of our test configs
    for config in CONFIGS:
        vultr.setup_platform(menuai, config, add_entities, None)

    return menuai_devices


@pytest.mark.usefixtures("valid_config")
def test_switch(menuai: menuai, menuai_devices: list[vultr.VultrSwitch]) -> None:
    """Test successful instance."""

    assert len(menuai_devices) == 3

    tested = 0

    for device in menuai_devices:
        if device.subscription == "555555":
            assert device.name == "Vultr {}"
            tested += 1

        device.update()
        device_attrs = device.extra_state_attributes

        if device.subscription == "555555":
            assert device.name == "Vultr Another Server"
            tested += 1

        if device.name == "A Server":
            assert device.is_on is True
            assert device.state == "on"
            assert device.icon == "mdi:server"
            assert device_attrs[ATTR_ALLOWED_BANDWIDTH] == "1000"
            assert device_attrs[ATTR_AUTO_BACKUPS] == "yes"
            assert device_attrs[ATTR_IPV4_ADDRESS] == "123.123.123.123"
            assert device_attrs[ATTR_COST_PER_MONTH] == "10.05"
            assert device_attrs[ATTR_CREATED_AT] == "2013-12-19 14:45:41"
            assert device_attrs[ATTR_SUBSCRIPTION_ID] == "576965"
            tested += 1

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
            tested += 1

    assert tested == 4


@pytest.mark.usefixtures("valid_config")
def test_turn_on(menuai: menuai, menuai_devices: list[vultr.VultrSwitch]) -> None:
    """Test turning a subscription on."""
    with (
        patch(
            "vultr.Vultr.server_list",
            return_value=json.loads(load_fixture("server_list.json", "vultr")),
        ),
        patch("vultr.Vultr.server_start") as mock_start,
    ):
        for device in menuai_devices:
            if device.name == "Failed Server":
                device.update()
                device.turn_on()

    # Turn on
    assert mock_start.call_count == 1


@pytest.mark.usefixtures("valid_config")
def test_turn_off(menuai: menuai, menuai_devices: list[vultr.VultrSwitch]) -> None:
    """Test turning a subscription off."""
    with (
        patch(
            "vultr.Vultr.server_list",
            return_value=json.loads(load_fixture("server_list.json", "vultr")),
        ),
        patch("vultr.Vultr.server_halt") as mock_halt,
    ):
        for device in menuai_devices:
            if device.name == "A Server":
                device.update()
                device.turn_off()

    # Turn off
    assert mock_halt.call_count == 1


def test_invalid_switch_config() -> None:
    """Test config type failures."""
    with pytest.raises(vol.Invalid):  # No subscription
        vultr.PLATFORM_SCHEMA({CONF_PLATFORM: base_vultr.DOMAIN})


@pytest.mark.usefixtures("valid_config")
def test_invalid_switches(menuai: menuai) -> None:
    """Test the VultrSwitch fails."""
    menuai_devices = []

    def add_entities(devices, action):
        """Mock add devices."""
        menuai_devices.extend(devices)

    bad_conf = {}  # No subscription

    vultr.setup_platform(menuai, bad_conf, add_entities, None)

    bad_conf = {
        CONF_NAME: "Missing Server",
        CONF_SUBSCRIPTION: "665544",
    }  # Sub not associated with API key (not in server_list)

    vultr.setup_platform(menuai, bad_conf, add_entities, None)
