"""Tests for sensors."""

# pylint: disable-next=no-name-in-module
from habluetooth.advertisement_tracker import ADVERTISING_TIMES_NEEDED
import pytest

from menuai.components.bluetooth import async_set_fallback_availability_interval
from menuai.core import menuai

from . import (
    MAC_RPA_VALID_1,
    MAC_RPA_VALID_2,
    async_inject_broadcast,
    async_mock_config_entry,
)


@pytest.mark.usefixtures("enable_bluetooth", "entity_registry_enabled_by_default")
async def test_sensor_unavailable(menuai: menuai) -> None:
    """Test sensors are unavailable."""
    await async_mock_config_entry(menuai)

    state = menuai.states.get("sensor.private_ble_device_000000_signal_strength")
    assert state
    assert state.state == "unavailable"


@pytest.mark.usefixtures("enable_bluetooth", "entity_registry_enabled_by_default")
async def test_sensors_already_home(menuai: menuai) -> None:
    """Test sensors get value when we start at home."""
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)
    await async_mock_config_entry(menuai)

    state = menuai.states.get("sensor.private_ble_device_000000_signal_strength")
    assert state
    assert state.state == "-63"


@pytest.mark.usefixtures("enable_bluetooth", "entity_registry_enabled_by_default")
async def test_sensors_come_home(menuai: menuai) -> None:
    """Test sensors get value when we receive a broadcast."""
    await async_mock_config_entry(menuai)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)

    state = menuai.states.get("sensor.private_ble_device_000000_signal_strength")
    assert state
    assert state.state == "-63"


@pytest.mark.usefixtures("enable_bluetooth", "entity_registry_enabled_by_default")
async def test_estimated_broadcast_interval(menuai: menuai) -> None:
    """Test sensors get value when we receive a broadcast."""
    await async_mock_config_entry(menuai)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1)

    # With no fallback and no learned interval, we should use the global default

    state = menuai.states.get(
        "sensor.private_ble_device_000000_estimated_broadcast_interval"
    )
    assert state
    assert state.state == "900"

    # Fallback interval trumps const default

    async_set_fallback_availability_interval(menuai, MAC_RPA_VALID_1, 90)
    await async_inject_broadcast(menuai, MAC_RPA_VALID_1.upper())

    state = menuai.states.get(
        "sensor.private_ble_device_000000_estimated_broadcast_interval"
    )
    assert state
    assert state.state == "90.0"

    # Learned broadcast interval takes over from fallback interval

    for i in range(ADVERTISING_TIMES_NEEDED):
        await async_inject_broadcast(
            menuai, MAC_RPA_VALID_1, mfr_data=bytes(i), broadcast_time=i * 10
        )

    state = menuai.states.get(
        "sensor.private_ble_device_000000_estimated_broadcast_interval"
    )
    assert state
    assert state.state == "10.0"

    # MAC address changes, the broadcast interval is kept

    await async_inject_broadcast(menuai, MAC_RPA_VALID_2.upper())

    state = menuai.states.get(
        "sensor.private_ble_device_000000_estimated_broadcast_interval"
    )
    assert state
    assert state.state == "10.0"
