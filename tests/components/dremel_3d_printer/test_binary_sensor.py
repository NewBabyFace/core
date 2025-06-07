"""Binary sensor tests for the Dremel 3D Printer integration."""

import pytest

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.components.dremel_3d_printer.const import DOMAIN
from menuai.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("connection", "entity_registry_enabled_by_default")
async def test_binary_sensors(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test we get binary sensor data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await async_setup_component(menuai, DOMAIN, {})
    state = menuai.states.get("binary_sensor.dremel_3d45_door")
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.DOOR
    assert state.state == STATE_OFF
    state = menuai.states.get("binary_sensor.dremel_3d45_running")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.RUNNING
