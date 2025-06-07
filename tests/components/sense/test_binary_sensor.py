"""The tests for Sense binary sensor platform."""

from datetime import timedelta
from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.sense.const import ACTIVE_UPDATE_RATE
from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from . import setup_platform
from .const import DEVICE_1_NAME, DEVICE_2_NAME

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_binary_sensors(
    menuai: menuai,
    mock_sense: MagicMock,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Sensor."""
    await setup_platform(menuai, config_entry, Platform.BINARY_SENSOR)
    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_on_off_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_sense: MagicMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test the Sense binary sensors."""
    await setup_platform(menuai, config_entry, BINARY_SENSOR_DOMAIN)
    device_1, device_2 = mock_sense.devices

    state = menuai.states.get(f"binary_sensor.{DEVICE_1_NAME.lower()}_power")
    assert state.state == STATE_OFF

    state = menuai.states.get(f"binary_sensor.{DEVICE_2_NAME.lower()}_power")
    assert state.state == STATE_OFF

    device_1.is_on = True
    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=ACTIVE_UPDATE_RATE))
    await menuai.async_block_till_done()

    state = menuai.states.get(f"binary_sensor.{DEVICE_1_NAME.lower()}_power")
    assert state.state == STATE_ON

    state = menuai.states.get(f"binary_sensor.{DEVICE_2_NAME.lower()}_power")
    assert state.state == STATE_OFF

    device_1.is_on = False
    device_2.is_on = True
    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=ACTIVE_UPDATE_RATE))
    await menuai.async_block_till_done()

    state = menuai.states.get(f"binary_sensor.{DEVICE_1_NAME.lower()}_power")
    assert state.state == STATE_OFF

    state = menuai.states.get(f"binary_sensor.{DEVICE_2_NAME.lower()}_power")
    assert state.state == STATE_ON
