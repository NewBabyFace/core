"""Tests for the EnergyZero integration."""

from unittest.mock import MagicMock, patch

from energyzero import EnergyZeroConnectionError
import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_energyzero")
async def test_load_unload_config_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test the EnergyZero configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@patch(
    "menuai.components.energyzero.coordinator.EnergyZero._request",
    side_effect=EnergyZeroConnectionError,
)
async def test_config_flow_entry_not_ready(
    mock_request: MagicMock,
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the EnergyZero configuration entry not ready."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_request.call_count == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
