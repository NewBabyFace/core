"""Tests for JVC Projector config entry."""

from datetime import timedelta
from unittest.mock import AsyncMock

from jvcprojector import JvcProjectorAuthError, JvcProjectorConnectError

from menuai.components.jvc_projector.coordinator import (
    INTERVAL_FAST,
    INTERVAL_SLOW,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.util.dt import utcnow

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_coordinator_update(
    menuai: menuai,
    mock_device: AsyncMock,
    mock_integration: MockConfigEntry,
) -> None:
    """Test coordinator update runs."""
    mock_device.get_state.return_value = {"power": "standby", "input": "hdmi1"}
    async_fire_time_changed(
        menuai, utcnow() + timedelta(seconds=INTERVAL_SLOW.seconds + 1)
    )
    await menuai.async_block_till_done()
    assert mock_device.get_state.call_count == 3
    coordinator = mock_integration.runtime_data
    assert coordinator.update_interval == INTERVAL_SLOW


async def test_coordinator_connect_error(
    menuai: menuai,
    mock_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator connect error."""
    mock_device.get_state.side_effect = JvcProjectorConnectError
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_coordinator_auth_error(
    menuai: menuai,
    mock_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator auth error."""
    mock_device.get_state.side_effect = JvcProjectorAuthError
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_coordinator_device_on(
    menuai: menuai,
    mock_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test coordinator changes update interval when device is on."""
    mock_device.get_state.return_value = {"power": "on", "input": "hdmi1"}
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    coordinator = mock_config_entry.runtime_data
    assert coordinator.update_interval == INTERVAL_FAST
