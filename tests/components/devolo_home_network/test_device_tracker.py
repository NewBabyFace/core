"""Tests for the devolo Home Network device tracker."""

from unittest.mock import AsyncMock

from devolo_plc_api.exceptions.device import DeviceUnavailable
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.device_tracker import DOMAIN as PLATFORM
from menuai.components.devolo_home_network.const import (
    DOMAIN,
    LONG_UPDATE_INTERVAL,
)
from menuai.const import STATE_NOT_HOME, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .const import CONNECTED_STATIONS, DISCOVERY_INFO, NO_CONNECTED_STATIONS
from .mock import MockDevice

from tests.common import async_fire_time_changed

STATION = CONNECTED_STATIONS[0]
SERIAL = DISCOVERY_INFO.properties["SN"]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_device_tracker(
    menuai: menuai,
    mock_device: MockDevice,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test device tracker states."""
    state_key = (
        f"{PLATFORM}.{DOMAIN}_{SERIAL}_{STATION.mac_address.lower().replace(':', '_')}"
    )
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    freezer.tick(LONG_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert menuai.states.get(state_key) == snapshot

    # Emulate state change
    mock_device.device.async_get_wifi_connected_station = AsyncMock(
        return_value=NO_CONNECTED_STATIONS
    )
    freezer.tick(LONG_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_NOT_HOME

    # Emulate device failure
    mock_device.device.async_get_wifi_connected_station = AsyncMock(
        side_effect=DeviceUnavailable
    )
    freezer.tick(LONG_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_restoring_clients(
    menuai: menuai,
    mock_device: MockDevice,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test restoring existing device_tracker entities."""
    state_key = (
        f"{PLATFORM}.{DOMAIN}_{SERIAL}_{STATION.mac_address.lower().replace(':', '_')}"
    )
    entry = configure_integration(menuai)
    entity_registry.async_get_or_create(
        PLATFORM,
        DOMAIN,
        f"{SERIAL}_{STATION.mac_address}",
        config_entry=entry,
    )

    mock_device.device.async_get_wifi_connected_station = AsyncMock(
        return_value=NO_CONNECTED_STATIONS
    )

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_NOT_HOME
