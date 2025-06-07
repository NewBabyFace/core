"""Tests for the Rituals Perfume Genie binary sensor platform."""

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.const import ATTR_DEVICE_CLASS, STATE_ON, EntityCategory
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import (
    init_integration,
    mock_config_entry,
    mock_diffuser_v1_battery_cartridge,
)


async def test_binary_sensors(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test the creation and values of the Rituals Perfume Genie binary sensor."""
    config_entry = mock_config_entry(unique_id="binary_sensor_test_diffuser_v1")
    diffuser = mock_diffuser_v1_battery_cartridge()
    await init_integration(menuai, config_entry, [diffuser])
    hublot = diffuser.hublot

    state = menuai.states.get("binary_sensor.genie_charging")
    assert state
    assert state.state == STATE_ON
    assert (
        state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.BATTERY_CHARGING
    )

    entry = entity_registry.async_get("binary_sensor.genie_charging")
    assert entry
    assert entry.unique_id == f"{hublot}-charging"
    assert entry.entity_category == EntityCategory.DIAGNOSTIC
