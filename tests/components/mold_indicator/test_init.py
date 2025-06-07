"""Test Mold indicator component setup process."""

from __future__ import annotations

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(loaded_entry.entry_id)
    await menuai.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED
