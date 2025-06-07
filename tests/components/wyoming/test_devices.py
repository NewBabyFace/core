"""Test Wyoming devices."""

from __future__ import annotations

from menuai.components.assist_pipeline.select import OPTION_PREFERRED
from menuai.components.wyoming import DOMAIN
from menuai.components.wyoming.devices import SatelliteDevice
from menuai.config_entries import ConfigEntry
from menuai.const import STATE_OFF
from menuai.core import menuai
from menuai.helpers import device_registry as dr


async def test_device_registry_info(
    menuai: menuai,
    satellite_device: SatelliteDevice,
    satellite_config_entry: ConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test info in device registry."""

    # Satellite uses config entry id since only one satellite per entry is
    # supported.
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, satellite_config_entry.entry_id)}
    )
    assert device is not None
    assert device.name == "Test Satellite"
    assert device.suggested_area == "Office"

    # Check associated entities
    assist_in_progress_id = satellite_device.get_assist_in_progress_entity_id(menuai)
    assert assist_in_progress_id
    assist_in_progress_state = menuai.states.get(assist_in_progress_id)
    # assist_in_progress binary sensor is disabled
    assert assist_in_progress_state is None

    muted_id = satellite_device.get_muted_entity_id(menuai)
    assert muted_id
    muted_state = menuai.states.get(muted_id)
    assert muted_state is not None
    assert muted_state.state == STATE_OFF

    pipeline_entity_id = satellite_device.get_pipeline_entity_id(menuai)
    assert pipeline_entity_id
    pipeline_state = menuai.states.get(pipeline_entity_id)
    assert pipeline_state is not None
    assert pipeline_state.state == OPTION_PREFERRED


async def test_remove_device_registry_entry(
    menuai: menuai,
    satellite_device: SatelliteDevice,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test removing a device registry entry."""

    # Check associated entities
    assist_in_progress_id = satellite_device.get_assist_in_progress_entity_id(menuai)
    assert assist_in_progress_id
    # assist_in_progress binary sensor is disabled
    assert menuai.states.get(assist_in_progress_id) is None

    muted_id = satellite_device.get_muted_entity_id(menuai)
    assert muted_id
    assert menuai.states.get(muted_id) is not None

    pipeline_entity_id = satellite_device.get_pipeline_entity_id(menuai)
    assert pipeline_entity_id
    assert menuai.states.get(pipeline_entity_id) is not None

    # Remove
    device_registry.async_remove_device(satellite_device.device_id)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    # Everything should be gone
    assert menuai.states.get(assist_in_progress_id) is None
    assert menuai.states.get(muted_id) is None
    assert menuai.states.get(pipeline_entity_id) is None
