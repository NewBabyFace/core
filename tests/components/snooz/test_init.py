"""Test Snooz configuration."""

from __future__ import annotations

from menuai.core import menuai

from . import SnoozFixture


async def test_removing_entry_cleans_up_connections(
    menuai: menuai, mock_connected_snooz: SnoozFixture
) -> None:
    """Tests setup and removal of a config entry, ensuring connections are cleaned up."""
    await menuai.config_entries.async_remove(mock_connected_snooz.entry.entry_id)
    await menuai.async_block_till_done()

    assert not mock_connected_snooz.device.is_connected


async def test_reloading_entry_cleans_up_connections(
    menuai: menuai, mock_connected_snooz: SnoozFixture
) -> None:
    """Test reloading an entry disconnects any existing connections."""
    await menuai.config_entries.async_reload(mock_connected_snooz.entry.entry_id)
    await menuai.async_block_till_done()

    assert not mock_connected_snooz.device.is_connected
