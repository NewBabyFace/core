"""Tests for polling measures."""

import time

# pylint: disable-next=no-name-in-module
from habluetooth.advertisement_tracker import ADVERTISING_TIMES_NEEDED
import pytest

from menuai.components.bluetooth.api import (
    async_get_fallback_availability_interval,
)
from menuai.core import menuai

from . import (
    MAC_RPA_VALID_1,
    MAC_RPA_VALID_2,
    MAC_STATIC,
    async_inject_broadcast,
    async_mock_config_entry,
    async_move_time_forwards,
)

from tests.components.bluetooth.test_advertisement_tracker import ONE_HOUR_SECONDS


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_created(menuai: menuai) -> None:
    """Test creating a tracker entity when no devices have been seen."""
    await async_mock_config_entry(menuai)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_ignore_other_rpa(menuai: menuai) -> None:
    """Test that tracker ignores RPA's that don't match us."""
    await async_mock_config_entry(menuai)
    await async_inject_broadcast(menuai, MAC_STATIC)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_already_home(menuai: menuai) -> None:
    """Test creating a tracker and the device was already discovered by HA."""
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)
    await async_mock_config_entry(menuai)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_arrive_home(menuai: menuai) -> None:
    """Test transition from not_home to home."""
    await async_mock_config_entry(menuai)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1, b"1")
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"
    assert state.attributes["current_address"] == "40:01:02:0a:c4:a6"
    assert state.attributes["source"] == "local"

    await async_inject_broadcast(menuai, MAC_STATIC, b"1")
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    # Test same wrong mac address again to exercise some caching
    await async_inject_broadcast(menuai, MAC_STATIC, b"2")
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    # And test original mac address again.
    # Use different mfr data so that event bubbles up
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1, b"2")
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"
    assert state.attributes["current_address"] == "40:01:02:0a:c4:a6"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_isolation(menuai: menuai) -> None:
    """Test creating 2 tracker entities doesn't confuse anything."""
    await async_mock_config_entry(menuai)
    await async_mock_config_entry(menuai, irk="1" * 32)

    # This broadcast should only impact the first entity
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1, b"1")

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    state = menuai.states.get("device_tracker.private_ble_device_111111")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_mac_rotate(menuai: menuai) -> None:
    """Test MAC address rotation."""
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)
    await async_mock_config_entry(menuai)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"
    assert state.attributes["current_address"] == MAC_RPA_VALID_1

    await async_inject_broadcast(menuai, MAC_RPA_VALID_2)
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"
    assert state.attributes["current_address"] == MAC_RPA_VALID_2


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_start_stale(menuai: menuai) -> None:
    """Test edge case where we find an existing stale record, and it expires before we see any more."""
    time.monotonic()

    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)
    await async_mock_config_entry(menuai)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    await async_move_time_forwards(
        menuai, ((ADVERTISING_TIMES_NEEDED - 1) * ONE_HOUR_SECONDS)
    )
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_tracker_leave_home(menuai: menuai) -> None:
    """Test tracker notices we have left."""
    time.monotonic()

    await async_mock_config_entry(menuai)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    await async_move_time_forwards(
        menuai, ((ADVERTISING_TIMES_NEEDED - 1) * ONE_HOUR_SECONDS)
    )
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth")
async def test_old_tracker_leave_home(menuai: menuai) -> None:
    """Test tracker ignores an old stale mac address timing out."""
    start_time = time.monotonic()

    await async_mock_config_entry(menuai)

    await async_inject_broadcast(menuai, MAC_RPA_VALID_2, broadcast_time=start_time)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_2, broadcast_time=start_time + 15)

    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    # First address has timed out - still home
    await async_move_time_forwards(menuai, 910)
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "home"

    # Second address has time out - now away
    await async_move_time_forwards(menuai, 920)
    state = menuai.states.get("device_tracker.private_ble_device_000000")
    assert state
    assert state.state == "not_home"


@pytest.mark.usefixtures("enable_bluetooth", "entity_registry_enabled_by_default")
async def test_mac_rotation(menuai: menuai) -> None:
    """Test sensors get value when we receive a broadcast."""
    await async_mock_config_entry(menuai)

    assert async_get_fallback_availability_interval(menuai, MAC_RPA_VALID_1) is None
    assert async_get_fallback_availability_interval(menuai, MAC_RPA_VALID_2) is None

    for i in range(ADVERTISING_TIMES_NEEDED):
        await async_inject_broadcast(
            menuai, MAC_RPA_VALID_1, mfr_data=bytes(i), broadcast_time=i * 10
        )

    await async_inject_broadcast(menuai, MAC_RPA_VALID_2)
    assert async_get_fallback_availability_interval(menuai, MAC_RPA_VALID_2) == 10
