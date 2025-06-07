"""Test Dynalite cover."""

from collections.abc import Callable
from unittest.mock import Mock

from dynalite_devices_lib.cover import DynaliteTimeCoverWithTiltDevice
from dynalite_devices_lib.dynalitebase import DynaliteBaseDevice
import pytest

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverState,
)
from menuai.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME
from menuai.core import menuai, State
from menuai.exceptions import menuaiError

from .common import (
    ATTR_ARGS,
    ATTR_METHOD,
    ATTR_SERVICE,
    create_entity_from_device,
    create_mock_device,
    run_service_tests,
)

from tests.common import mock_restore_cache


@pytest.fixture
def mock_device() -> Mock:
    """Mock a Dynalite device."""
    mock_dev = create_mock_device("cover", DynaliteTimeCoverWithTiltDevice)
    mock_dev.device_class = CoverDeviceClass.BLIND.value
    mock_dev.current_cover_position = 0
    mock_dev.current_cover_tilt_position = 0
    mock_dev.is_opening = False
    mock_dev.is_closing = False
    mock_dev.is_closed = True

    def mock_init_level(target):
        mock_dev.is_closed = target == 0

    type(mock_dev).init_level = Mock(side_effect=mock_init_level)

    return mock_dev


async def test_cover_setup(menuai: menuai, mock_device: Mock) -> None:
    """Test a successful setup."""
    await create_entity_from_device(menuai, mock_device)
    entity_state = menuai.states.get("cover.name")
    assert entity_state.attributes[ATTR_FRIENDLY_NAME] == mock_device.name
    assert (
        entity_state.attributes[ATTR_CURRENT_POSITION]
        == mock_device.current_cover_position
    )
    assert (
        entity_state.attributes[ATTR_CURRENT_TILT_POSITION]
        == mock_device.current_cover_tilt_position
    )
    assert entity_state.attributes[ATTR_DEVICE_CLASS] == mock_device.device_class
    await run_service_tests(
        menuai,
        mock_device,
        "cover",
        [
            {ATTR_SERVICE: "open_cover", ATTR_METHOD: "async_open_cover"},
            {ATTR_SERVICE: "close_cover", ATTR_METHOD: "async_close_cover"},
            {ATTR_SERVICE: "stop_cover", ATTR_METHOD: "async_stop_cover"},
            {
                ATTR_SERVICE: "set_cover_position",
                ATTR_METHOD: "async_set_cover_position",
                ATTR_ARGS: {ATTR_POSITION: 50},
            },
            {ATTR_SERVICE: "open_cover_tilt", ATTR_METHOD: "async_open_cover_tilt"},
            {ATTR_SERVICE: "close_cover_tilt", ATTR_METHOD: "async_close_cover_tilt"},
            {ATTR_SERVICE: "stop_cover_tilt", ATTR_METHOD: "async_stop_cover_tilt"},
            {
                ATTR_SERVICE: "set_cover_tilt_position",
                ATTR_METHOD: "async_set_cover_tilt_position",
                ATTR_ARGS: {ATTR_TILT_POSITION: 50},
            },
        ],
    )


async def test_cover_without_tilt(menuai: menuai, mock_device: Mock) -> None:
    """Test a cover with no tilt."""
    mock_device.has_tilt = False
    await create_entity_from_device(menuai, mock_device)
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            "cover", "open_cover_tilt", {"entity_id": "cover.name"}, blocking=True
        )
    await menuai.async_block_till_done()
    mock_device.async_open_cover_tilt.assert_not_called()


async def check_cover_position(
    menuai: menuai,
    update_func: Callable[[DynaliteBaseDevice | None], None],
    device: Mock,
    closing: bool,
    opening: bool,
    closed: bool,
    expected: str,
) -> None:
    """Check that a given position behaves correctly."""
    device.is_closing = closing
    device.is_opening = opening
    device.is_closed = closed
    update_func(device)
    await menuai.async_block_till_done()
    entity_state = menuai.states.get("cover.name")
    assert entity_state.state == expected


async def test_cover_positions(menuai: menuai, mock_device: Mock) -> None:
    """Test that the state updates in the various positions."""
    update_func = await create_entity_from_device(menuai, mock_device)
    await check_cover_position(
        menuai, update_func, mock_device, True, False, False, CoverState.CLOSING
    )
    await check_cover_position(
        menuai, update_func, mock_device, False, True, False, CoverState.OPENING
    )
    await check_cover_position(
        menuai, update_func, mock_device, False, False, True, CoverState.CLOSED
    )
    await check_cover_position(
        menuai, update_func, mock_device, False, False, False, CoverState.OPEN
    )


async def test_cover_restore_state(menuai: menuai, mock_device: Mock) -> None:
    """Test restore from cache."""
    mock_restore_cache(
        menuai,
        [State("cover.name", CoverState.OPEN, attributes={ATTR_CURRENT_POSITION: 77})],
    )
    await create_entity_from_device(menuai, mock_device)
    mock_device.init_level.assert_called_once_with(77)
    entity_state = menuai.states.get("cover.name")
    assert entity_state.state == CoverState.OPEN


async def test_cover_restore_state_bad_cache(
    menuai: menuai, mock_device: Mock
) -> None:
    """Test restore from a cache without the attribute."""
    mock_restore_cache(
        menuai,
        [State("cover.name", CoverState.OPEN, attributes={"bla bla": 77})],
    )
    await create_entity_from_device(menuai, mock_device)
    mock_device.init_level.assert_not_called()
    entity_state = menuai.states.get("cover.name")
    assert entity_state.state == CoverState.CLOSED
