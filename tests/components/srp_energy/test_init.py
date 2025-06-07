"""Tests for Srp Energy component Init."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai


async def test_setup_entry(menuai: menuai, init_integration) -> None:
    """Test setup entry."""
    assert init_integration.state is ConfigEntryState.LOADED


async def test_unload_entry(menuai: menuai, init_integration) -> None:
    """Test being able to unload an entry."""
    assert init_integration.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(init_integration.entry_id)
    await menuai.async_block_till_done()
