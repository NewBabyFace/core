"""Tests for the Webmin integration."""

from menuai.components.webmin.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import async_init_integration


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""

    entry = await async_init_integration(menuai)

    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_entry_without_mac_address(menuai: menuai) -> None:
    """Test an entry without MAC address."""

    entry = await async_init_integration(menuai, False)

    assert entry.runtime_data.unique_id == entry.entry_id
