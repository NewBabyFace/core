"""Tests for the devolo Home Network sensors."""

from unittest.mock import AsyncMock

from devolo_plc_api.exceptions.device import DeviceUnavailable
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.binary_sensor import DOMAIN as PLATFORM
from menuai.components.devolo_home_network.const import LONG_UPDATE_INTERVAL
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import configure_integration
from .const import PLCNET_ATTACHED
from .mock import MockDevice

from tests.common import async_fire_time_changed


@pytest.mark.usefixtures("mock_device")
async def test_binary_sensor_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test default setup of the binary sensor component."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert entity_registry.async_get(
        f"{PLATFORM}.{device_name}_connected_to_router"
    ).disabled


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_update_attached_to_router(
    menuai: menuai,
    mock_device: MockDevice,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test state change of a attached_to_router binary sensor device."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    state_key = f"{PLATFORM}.{device_name}_connected_to_router"

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get(state_key) == snapshot
    assert entity_registry.async_get(state_key) == snapshot

    # Emulate device failure
    mock_device.plcnet.async_get_network_overview = AsyncMock(
        side_effect=DeviceUnavailable
    )
    freezer.tick(LONG_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    # Emulate state change
    mock_device.plcnet.async_get_network_overview = AsyncMock(
        return_value=PLCNET_ATTACHED
    )
    freezer.tick(LONG_UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state is not None
    assert state.state == STATE_ON
