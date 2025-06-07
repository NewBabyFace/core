"""Test ESPHome binary sensors."""

from aioesphomeapi import APIClient, BinarySensorInfo, BinarySensorState
import pytest

from menuai.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai

from .conftest import MockESPHomeDeviceType, MockGenericDeviceEntryType


@pytest.mark.parametrize(
    "binary_state", [(True, STATE_ON), (False, STATE_OFF), (None, STATE_UNKNOWN)]
)
async def test_binary_sensor_generic_entity(
    menuai: menuai,
    mock_client: APIClient,
    binary_state: tuple[bool, str],
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic binary_sensor entity."""
    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
            unique_id="my_binary_sensor",
        )
    ]
    esphome_state, menuai_state = binary_state
    states = [BinarySensorState(key=1, state=esphome_state)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("binary_sensor.test_mybinary_sensor")
    assert state is not None
    assert state.state == menuai_state


async def test_status_binary_sensor(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic binary_sensor entity."""
    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
            unique_id="my_binary_sensor",
            is_status_binary_sensor=True,
        )
    ]
    states = [BinarySensorState(key=1, state=None)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("binary_sensor.test_mybinary_sensor")
    assert state is not None
    assert state.state == STATE_ON


async def test_binary_sensor_missing_state(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic binary_sensor that is missing state."""
    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
            unique_id="my_binary_sensor",
        )
    ]
    states = [BinarySensorState(key=1, state=True, missing_state=True)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("binary_sensor.test_mybinary_sensor")
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_binary_sensor_has_state_false(
    menuai: menuai,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:
    """Test a generic binary_sensor where has_state is false."""
    entity_info = [
        BinarySensorInfo(
            object_id="mybinary_sensor",
            key=1,
            name="my binary_sensor",
            unique_id="my_binary_sensor",
        )
    ]
    states = []
    user_service = []
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("binary_sensor.test_mybinary_sensor")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    mock_device.set_state(BinarySensorState(key=1, state=True, missing_state=False))
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_mybinary_sensor")
    assert state is not None
    assert state.state == STATE_ON
