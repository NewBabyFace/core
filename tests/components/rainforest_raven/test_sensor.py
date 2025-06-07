"""Tests for the Rainforest RAVEn sensors."""

from datetime import timedelta
from unittest.mock import AsyncMock

from aioraven.device import RAVEnConnectionError
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import NETWORK_INFO

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("mock_entry")
async def test_sensors(
    menuai: menuai,
    mock_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the sensors."""
    assert len(menuai.states.async_all()) == 5

    await snapshot_platform(menuai, entity_registry, snapshot, mock_entry.entry_id)


@pytest.mark.usefixtures("mock_entry")
async def test_device_update_error(
    menuai: menuai,
    mock_device: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test handling of a device error during an update."""
    mock_device.get_network_info.side_effect = (RAVEnConnectionError, NETWORK_INFO)

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state != STATE_UNAVAILABLE for state in states)

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state == STATE_UNAVAILABLE for state in states)

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state != STATE_UNAVAILABLE for state in states)


@pytest.mark.usefixtures("mock_entry")
async def test_device_update_timeout(
    menuai: menuai, mock_device: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Test handling of a device timeout during an update."""
    mock_device.get_network_info.side_effect = (TimeoutError, NETWORK_INFO)

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state != STATE_UNAVAILABLE for state in states)

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state == STATE_UNAVAILABLE for state in states)

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)

    states = menuai.states.async_all()
    assert len(states) == 5
    assert all(state.state != STATE_UNAVAILABLE for state in states)


@pytest.mark.usefixtures("mock_entry")
async def test_device_cache(
    menuai: menuai, mock_device: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Test that the device isn't re-opened for subsequent refreshes."""
    assert mock_device.get_network_info.call_count == 1
    assert mock_device.open.call_count == 1

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert mock_device.get_network_info.call_count == 2
    assert mock_device.open.call_count == 1
