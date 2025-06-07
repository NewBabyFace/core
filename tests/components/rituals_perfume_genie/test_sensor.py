"""Tests for the Rituals Perfume Genie sensor platform."""

from menuai.components.rituals_perfume_genie.sensor import SensorDeviceClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    EntityCategory,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import (
    init_integration,
    mock_config_entry,
    mock_diffuser_v1_battery_cartridge,
)


async def test_sensors_diffuser_v1_battery_cartridge(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test the creation and values of the Rituals Perfume Genie sensors."""
    config_entry = mock_config_entry(unique_id="id_123_sensor_test_diffuser_v1")
    diffuser = mock_diffuser_v1_battery_cartridge()
    await init_integration(menuai, config_entry, [diffuser])
    hublot = diffuser.hublot

    state = menuai.states.get("sensor.genie_perfume")
    assert state
    assert state.state == diffuser.perfume

    entry = entity_registry.async_get("sensor.genie_perfume")
    assert entry
    assert entry.unique_id == f"{hublot}-perfume"

    state = menuai.states.get("sensor.genie_fill")
    assert state
    assert state.state == diffuser.fill

    entry = entity_registry.async_get("sensor.genie_fill")
    assert entry
    assert entry.unique_id == f"{hublot}-fill"

    state = menuai.states.get("sensor.genie_battery")
    assert state
    assert state.state == str(diffuser.battery_percentage)
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.BATTERY
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE

    entry = entity_registry.async_get("sensor.genie_battery")
    assert entry
    assert entry.unique_id == f"{hublot}-battery_percentage"
    assert entry.entity_category == EntityCategory.DIAGNOSTIC

    state = menuai.states.get("sensor.genie_wi_fi_signal")
    assert state
    assert state.state == str(diffuser.wifi_percentage)
    assert state.attributes.get(ATTR_DEVICE_CLASS) is None
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE

    entry = entity_registry.async_get("sensor.genie_wi_fi_signal")
    assert entry
    assert entry.unique_id == f"{hublot}-wifi_percentage"
    assert entry.entity_category == EntityCategory.DIAGNOSTIC
