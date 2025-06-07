"""Test the Advantage Air Binary Sensor Platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import add_mock_config

from tests.common import async_fire_time_changed


async def test_binary_sensor_async_setup_entry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
) -> None:
    """Test binary sensor setup."""

    await add_mock_config(menuai)

    # Test First Air Filter
    entity_id = "binary_sensor.myzone_filter"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-filter"

    # Test Second Air Filter
    entity_id = "binary_sensor.mytemp_filter"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac2-filter"

    # Test First Motion Sensor
    entity_id = "binary_sensor.myzone_zone_open_with_sensor_motion"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01-motion"

    # Test Second Motion Sensor
    entity_id = "binary_sensor.myzone_zone_closed_with_sensor_motion"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z02-motion"

    # Test First MyZone Sensor (disabled by default)
    entity_id = "binary_sensor.myzone_zone_open_with_sensor_myzone"

    assert not menuai.states.get(entity_id)

    mock_get.reset_mock()

    with patch("menuai.config_entries.RELOAD_AFTER_UPDATE_DELAY", 1):
        entity_registry.async_update_entity(entity_id=entity_id, disabled_by=None)
        await menuai.async_block_till_done()

        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(mock_get.mock_calls) == 1

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01-myzone"

    # Test Second Motion Sensor (disabled by default)
    entity_id = "binary_sensor.myzone_zone_closed_with_sensor_myzone"

    assert not menuai.states.get(entity_id)

    mock_get.reset_mock()

    with patch("menuai.config_entries.RELOAD_AFTER_UPDATE_DELAY", 1):
        entity_registry.async_update_entity(entity_id=entity_id, disabled_by=None)
        await menuai.async_block_till_done()

        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(mock_get.mock_calls) == 1

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z02-myzone"
