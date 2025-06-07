"""Tests for AVM Fritz!Box sensor component."""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import HTTPError
from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import PRESET_COMFORT, PRESET_ECO
from menuai.components.fritzbox.const import DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICES, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import (
    FritzDeviceBinarySensorMock,
    FritzDeviceClimateMock,
    FritzDeviceSensorMock,
    FritzDeviceSwitchMock,
    FritzEntityBaseMock,
    set_devices,
    setup_config_entry,
)
from .const import CONF_FAKE_NAME, MOCK_CONFIG

from tests.common import async_fire_time_changed, snapshot_platform

ENTITY_ID = f"{SENSOR_DOMAIN}.{CONF_FAKE_NAME}"


@pytest.mark.parametrize(
    "device",
    [
        FritzDeviceBinarySensorMock,
        FritzDeviceClimateMock,
        FritzDeviceSensorMock,
        FritzDeviceSwitchMock,
    ],
)
async def test_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    fritz: Mock,
    device: FritzEntityBaseMock,
) -> None:
    """Test setup of sensor platform for different device types."""
    device = device()

    with patch("menuai.components.fritzbox.PLATFORMS", [Platform.SENSOR]):
        entry = await setup_config_entry(
            menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0], ENTITY_ID, device, fritz
        )
    assert entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_update(menuai: menuai, fritz: Mock) -> None:
    """Test update without error."""
    device = FritzDeviceSensorMock()
    await setup_config_entry(
        menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0], ENTITY_ID, device, fritz
    )
    assert fritz().update_devices.call_count == 1
    assert fritz().login.call_count == 1

    next_update = dt_util.utcnow() + timedelta(seconds=200)
    async_fire_time_changed(menuai, next_update)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert fritz().update_devices.call_count == 2
    assert fritz().login.call_count == 1


async def test_update_error(menuai: menuai, fritz: Mock) -> None:
    """Test update with error."""
    device = FritzDeviceSensorMock()
    fritz().update_devices.side_effect = HTTPError("Boom")
    entry = await setup_config_entry(
        menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0], ENTITY_ID, device, fritz
    )
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert fritz().update_devices.call_count == 2
    assert fritz().login.call_count == 2

    next_update = dt_util.utcnow() + timedelta(seconds=200)
    async_fire_time_changed(menuai, next_update)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert fritz().update_devices.call_count == 4
    assert fritz().login.call_count == 4


async def test_discover_new_device(menuai: menuai, fritz: Mock) -> None:
    """Test adding new discovered devices during runtime."""
    device = FritzDeviceSensorMock()
    await setup_config_entry(
        menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0], ENTITY_ID, device, fritz
    )

    state = menuai.states.get(f"{ENTITY_ID}_temperature")
    assert state

    new_device = FritzDeviceSensorMock()
    new_device.ain = "7890 1234"
    new_device.device_and_unit_id = ("7890 1234", None)
    new_device.name = "new_device"
    set_devices(fritz, devices=[device, new_device])

    next_update = dt_util.utcnow() + timedelta(seconds=200)
    async_fire_time_changed(menuai, next_update)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(f"{SENSOR_DOMAIN}.new_device_temperature")
    assert state


@pytest.mark.parametrize(
    ("next_changes", "expected_states"),
    [
        (
            [0, 16],
            [STATE_UNKNOWN, STATE_UNKNOWN, STATE_UNKNOWN, STATE_UNKNOWN],
        ),
        (
            [0, 22],
            [STATE_UNKNOWN, STATE_UNKNOWN, STATE_UNKNOWN, STATE_UNKNOWN],
        ),
        (
            [1726855200, 16.0],
            ["2024-09-20T18:00:00+00:00", "16.0", PRESET_ECO, PRESET_COMFORT],
        ),
        (
            [1726855200, 22.0],
            ["2024-09-20T18:00:00+00:00", "22.0", PRESET_COMFORT, PRESET_ECO],
        ),
    ],
)
async def test_next_change_sensors(
    menuai: menuai, fritz: Mock, next_changes: list, expected_states: list
) -> None:
    """Test next change sensors."""
    device = FritzDeviceClimateMock()
    device.nextchange_endperiod = next_changes[0]
    device.nextchange_temperature = next_changes[1]

    await setup_config_entry(
        menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0], ENTITY_ID, device, fritz
    )

    base_name = f"{SENSOR_DOMAIN}.{CONF_FAKE_NAME}"

    state = menuai.states.get(f"{base_name}_next_scheduled_change_time")
    assert state
    assert state.state == expected_states[0]

    state = menuai.states.get(f"{base_name}_next_scheduled_temperature")
    assert state
    assert state.state == expected_states[1]

    state = menuai.states.get(f"{base_name}_next_scheduled_preset")
    assert state
    assert state.state == expected_states[2]

    state = menuai.states.get(f"{base_name}_current_scheduled_preset")
    assert state
    assert state.state == expected_states[3]
