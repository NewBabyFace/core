"""Tests for the AsusWrt integration."""

from menuai.components.asuswrt.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai

from .common import CONFIG_DATA_TELNET, ROUTER_MAC_ADDR

from tests.common import MockConfigEntry


async def test_disconnect_on_stop(menuai: menuai, connect_legacy) -> None:
    """Test we close the connection with the router when MenuAIs stops."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG_DATA_TELNET,
        unique_id=ROUTER_MAC_ADDR,
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()

    assert connect_legacy.return_value.connection.disconnect.call_count == 1
    assert config_entry.state is ConfigEntryState.LOADED
