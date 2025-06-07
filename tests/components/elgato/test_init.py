"""Tests for the Elgato Key Light integration."""

from unittest.mock import MagicMock

from elgato import ElgatoConnectionError

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_elgato: MagicMock,
) -> None:
    """Test the Elgato configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert len(mock_elgato.info.mock_calls) == 1

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_elgato: MagicMock,
) -> None:
    """Test the Elgato configuration entry not ready."""
    mock_elgato.state.side_effect = ElgatoConnectionError

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert len(mock_elgato.state.mock_calls) == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
