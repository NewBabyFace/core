"""Test loading of the Tibber config entry."""

from unittest.mock import MagicMock

from menuai.components.recorder import Recorder
from menuai.components.tibber import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai


async def test_entry_unload(
    recorder_mock: Recorder, menuai: menuai, mock_tibber_setup: MagicMock
) -> None:
    """Test unloading the entry."""
    entry = menuai.config_entries.async_entry_for_domain_unique_id(DOMAIN, "tibber")
    assert entry.state == ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    mock_tibber_setup.rt_disconnect.assert_called_once()
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert entry.state == ConfigEntryState.NOT_LOADED
