"""Tests for the sensor provided by the CPU Speed integration."""

from unittest.mock import MagicMock

from menuai.components.cpuspeed.const import DOMAIN
from menuai.components.cpuspeed.sensor import ATTR_ARCH, ATTR_BRAND, ATTR_HZ
from menuai.components.menuai import (
    DOMAIN as HOME_ASSISTANT_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.sensor import SensorDeviceClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_sensor(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cpuinfo: MagicMock,
    init_integration: MockConfigEntry,
) -> None:
    """Test the CPU Speed sensor."""
    await async_setup_component(menuai, "menuai", {})

    entry = entity_registry.async_get("sensor.cpu_speed")
    assert entry
    assert entry.unique_id == entry.config_entry_id
    assert entry.entity_category is None

    state = menuai.states.get("sensor.cpu_speed")
    assert state
    assert state.state == "3.2"
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "CPU Speed"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.FREQUENCY

    assert state.attributes.get(ATTR_ARCH) == "aargh"
    assert state.attributes.get(ATTR_BRAND) == "Intel Ryzen 7"
    assert state.attributes.get(ATTR_HZ) == 3.6

    mock_cpuinfo.return_value = {}
    await menuai.services.async_call(
        HOME_ASSISTANT_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: "sensor.cpu_speed"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.cpu_speed")
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ARCH) == "aargh"
    assert state.attributes.get(ATTR_BRAND) == "Intel Ryzen 7"
    assert state.attributes.get(ATTR_HZ) == 3.6

    assert entry.device_id
    device_entry = device_registry.async_get(entry.device_id)
    assert device_entry
    assert device_entry.identifiers == {(DOMAIN, entry.config_entry_id)}
    assert device_entry.name == "CPU Speed"


async def test_sensor_partial_info(
    menuai: menuai,
    mock_cpuinfo: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the CPU Speed sensor missing info."""
    mock_config_entry.add_to_menuai(menuai)

    # Pop some info from the mocked CPUSpeed
    mock_cpuinfo.return_value.pop("brand_raw")
    mock_cpuinfo.return_value.pop("arch_string_raw")

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.cpu_speed")
    assert state
    assert state.state == "3.2"
    assert state.attributes.get(ATTR_ARCH) is None
    assert state.attributes.get(ATTR_BRAND) is None
