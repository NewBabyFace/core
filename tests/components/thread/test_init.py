"""Test the Thread integration."""

from menuai.components import thread
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_create_entry(menuai: menuai) -> None:
    """Test an entry is created by async_setup."""
    assert len(menuai.config_entries.async_entries(thread.DOMAIN)) == 0
    assert await async_setup_component(menuai, thread.DOMAIN, {})
    await menuai.async_block_till_done()

    assert len(menuai.config_entries.async_entries(thread.DOMAIN)) == 1


async def test_remove_entry(menuai: menuai, thread_config_entry) -> None:
    """Test removing the entry."""

    config_entry = menuai.config_entries.async_entries(thread.DOMAIN)[0]
    assert await menuai.config_entries.async_remove(config_entry.entry_id) == {
        "require_restart": False
    }


async def test_import_once(menuai: menuai, thread_config_entry) -> None:
    """Test only a single entry is created."""
    await menuai.async_block_till_done()
    assert len(menuai.config_entries.async_entries(thread.DOMAIN)) == 1
