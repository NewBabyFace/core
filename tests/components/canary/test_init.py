"""The tests for the Canary component."""

from requests import ConnectTimeout

from menuai.components.canary.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_integration


async def test_unload_entry(menuai: menuai, canary) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert entry
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_raises_entry_not_ready(menuai: menuai, canary) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    canary.side_effect = ConnectTimeout()

    entry = await init_integration(menuai)
    assert entry
    assert entry.state is ConfigEntryState.SETUP_RETRY
