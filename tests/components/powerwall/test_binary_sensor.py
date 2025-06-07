"""The binary sensor tests for the powerwall platform."""

from unittest.mock import patch

from menuai.components.powerwall.const import DOMAIN
from menuai.const import CONF_IP_ADDRESS, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai

from .mocks import _mock_powerwall_with_fixtures

from tests.common import MockConfigEntry


async def test_sensors(menuai: menuai) -> None:
    """Test creation of the binary sensors."""

    mock_powerwall = await _mock_powerwall_with_fixtures(menuai)

    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_IP_ADDRESS: "1.2.3.4"})
    config_entry.add_to_menuai(menuai)
    with (
        patch(
            "menuai.components.powerwall.config_flow.Powerwall",
            return_value=mock_powerwall,
        ),
        patch(
            "menuai.components.powerwall.Powerwall", return_value=mock_powerwall
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.mysite_grid_services_active")
    assert state.state == STATE_ON
    expected_attributes = {
        "friendly_name": "MySite Grid services active",
        "device_class": "power",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(item in state.attributes.items() for item in expected_attributes.items())

    state = menuai.states.get("binary_sensor.mysite_grid_status")
    assert state.state == STATE_ON
    expected_attributes = {
        "friendly_name": "MySite Grid status",
        "device_class": "power",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(item in state.attributes.items() for item in expected_attributes.items())

    state = menuai.states.get("binary_sensor.mysite_status")
    assert state.state == STATE_ON
    expected_attributes = {
        "friendly_name": "MySite Status",
        "device_class": "power",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(item in state.attributes.items() for item in expected_attributes.items())

    state = menuai.states.get("binary_sensor.mysite_connected_to_tesla")
    assert state.state == STATE_ON
    expected_attributes = {
        "friendly_name": "MySite Connected to Tesla",
        "device_class": "connectivity",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(item in state.attributes.items() for item in expected_attributes.items())

    state = menuai.states.get("binary_sensor.mysite_charging")
    assert state.state == STATE_ON
    expected_attributes = {
        "friendly_name": "MySite Charging",
        "device_class": "battery_charging",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(item in state.attributes.items() for item in expected_attributes.items())


async def test_sensors_with_empty_meters(menuai: menuai) -> None:
    """Test creation of the binary sensors with empty meters."""

    mock_powerwall = await _mock_powerwall_with_fixtures(menuai, empty_meters=True)

    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_IP_ADDRESS: "1.2.3.4"})
    config_entry.add_to_menuai(menuai)
    with (
        patch(
            "menuai.components.powerwall.config_flow.Powerwall",
            return_value=mock_powerwall,
        ),
        patch(
            "menuai.components.powerwall.Powerwall", return_value=mock_powerwall
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.mysite_charging")
    assert state.state == STATE_UNAVAILABLE
