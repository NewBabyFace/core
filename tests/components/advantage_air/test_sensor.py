"""Test the Advantage Air Sensor Platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from menuai.components.advantage_air.const import DOMAIN
from menuai.components.advantage_air.sensor import (
    ADVANTAGE_AIR_SERVICE_SET_TIME_TO,
    ADVANTAGE_AIR_SET_COUNTDOWN_VALUE,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import add_mock_config

from tests.common import async_fire_time_changed


async def test_sensor_platform(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
) -> None:
    """Test sensor platform."""

    await add_mock_config(menuai)

    # Test First TimeToOn Sensor
    entity_id = "sensor.myzone_time_to_on"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 0

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-timetoOn"

    value = 20

    await menuai.services.async_call(
        DOMAIN,
        ADVANTAGE_AIR_SERVICE_SET_TIME_TO,
        {ATTR_ENTITY_ID: [entity_id], ADVANTAGE_AIR_SET_COUNTDOWN_VALUE: value},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test First TimeToOff Sensor
    entity_id = "sensor.myzone_time_to_off"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 10

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-timetoOff"

    value = 0
    await menuai.services.async_call(
        DOMAIN,
        ADVANTAGE_AIR_SERVICE_SET_TIME_TO,
        {ATTR_ENTITY_ID: [entity_id], ADVANTAGE_AIR_SET_COUNTDOWN_VALUE: value},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test First Zone Vent Sensor
    entity_id = "sensor.myzone_zone_open_with_sensor_vent"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 100

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01-vent"

    # Test Second Zone Vent Sensor
    entity_id = "sensor.myzone_zone_closed_with_sensor_vent"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 0

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z02-vent"

    # Test First Zone Signal Sensor
    entity_id = "sensor.myzone_zone_open_with_sensor_signal"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 40

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01-signal"

    # Test Second Zone Signal Sensor
    entity_id = "sensor.myzone_zone_closed_with_sensor_signal"
    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 10

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z02-signal"


async def test_sensor_platform_disabled_entity(
    menuai: menuai, entity_registry: er.EntityRegistry, mock_get: AsyncMock
) -> None:
    """Test sensor platform disabled entity."""

    await add_mock_config(menuai)

    # Test First Zone Temp Sensor (disabled by default)
    entity_id = "sensor.myzone_zone_open_with_sensor_temperature"

    assert not menuai.states.get(entity_id)

    mock_get.reset_mock()

    with patch("menuai.config_entries.RELOAD_AFTER_UPDATE_DELAY", 1):
        entity_registry.async_update_entity(entity_id=entity_id, disabled_by=None)
        await menuai.async_block_till_done(wait_background_tasks=True)

        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(mock_get.mock_calls) == 1

    state = menuai.states.get(entity_id)
    assert state
    assert int(state.state) == 25

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01-temp"
