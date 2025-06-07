"""Test the Met Éireann integration init."""

from menuai.components.met_eireann.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_integration


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
