"""Tests for the local_ip component."""

from __future__ import annotations

from menuai.components.local_ip.const import DOMAIN
from menuai.components.network import MDNS_TARGET_IP, async_get_source_ip
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_basic_setup(menuai: menuai) -> None:
    """Test component setup creates entry from config."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    local_ip = await async_get_source_ip(menuai, target_ip=MDNS_TARGET_IP)
    state = menuai.states.get(f"sensor.{DOMAIN}")
    assert state
    assert state.state == local_ip

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
