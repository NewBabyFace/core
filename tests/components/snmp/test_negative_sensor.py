"""SNMP sensor tests."""

from unittest.mock import patch

from pysnmp.proto.rfc1902 import Integer32
import pytest

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
def hlapi_mock():
    """Mock out 3rd party API."""
    mock_data = Integer32(-13)
    with patch(
        "menuai.components.snmp.sensor.getCmd",
        return_value=(None, None, None, [[mock_data]]),
    ):
        yield


async def test_basic_config(menuai: menuai) -> None:
    """Test basic entity configuration."""

    config = {
        SENSOR_DOMAIN: {
            "platform": "snmp",
            "host": "192.168.1.32",
            "baseoid": "1.3.6.1.4.1.2021.10.1.3.1",
        },
    }

    assert await async_setup_component(menuai, SENSOR_DOMAIN, config)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.snmp")
    assert state.state == "-13"
    assert state.attributes == {"friendly_name": "SNMP"}


async def test_entity_config(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test entity configuration."""

    config = {
        SENSOR_DOMAIN: {
            # SNMP configuration
            "platform": "snmp",
            "host": "192.168.1.32",
            "baseoid": "1.3.6.1.4.1.2021.10.1.3.1",
            # Entity configuration
            "icon": "{{'mdi:one_two_three'}}",
            "picture": "{{'blabla.png'}}",
            "device_class": "temperature",
            "name": "{{'SNMP' + ' ' + 'Sensor'}}",
            "state_class": "measurement",
            "unique_id": "very_unique",
            "unit_of_measurement": "°C",
        },
    }

    assert await async_setup_component(menuai, SENSOR_DOMAIN, config)
    await menuai.async_block_till_done()

    assert entity_registry.async_get("sensor.snmp_sensor").unique_id == "very_unique"

    state = menuai.states.get("sensor.snmp_sensor")
    assert state.state == "-13"
    assert state.attributes == {
        "device_class": "temperature",
        "entity_picture": "blabla.png",
        "friendly_name": "SNMP Sensor",
        "icon": "mdi:one_two_three",
        "state_class": "measurement",
        "unit_of_measurement": "°C",
    }
