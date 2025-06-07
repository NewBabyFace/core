"""Test the Model Context Protocol Server init module."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_init(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test the integration is initialized and can be unloaded cleanly."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
