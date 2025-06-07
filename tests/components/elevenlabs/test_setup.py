"""Tests for the ElevenLabs TTS entity."""

from __future__ import annotations

from unittest.mock import MagicMock

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_setup(
    menuai: menuai,
    mock_async_client: MagicMock,
    mock_entry: MockConfigEntry,
) -> None:
    """Test entry setup without any exceptions."""
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    assert mock_entry.state == ConfigEntryState.LOADED
    # Unload
    await menuai.config_entries.async_unload(mock_entry.entry_id)
    assert mock_entry.state == ConfigEntryState.NOT_LOADED


async def test_setup_connect_error(
    menuai: menuai,
    mock_async_client_connect_error: MagicMock,
    mock_entry: MockConfigEntry,
) -> None:
    """Test entry setup with a connection error."""
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    # Ensure is not ready
    assert mock_entry.state == ConfigEntryState.SETUP_RETRY
