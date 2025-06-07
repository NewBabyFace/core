"""Test the WS66i 6-Zone Amplifier init file."""

from unittest.mock import patch

from menuai.components.ws66i.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .test_media_player import (
    MOCK_CONFIG,
    MOCK_DEFAULT_OPTIONS,
    MOCK_OPTIONS,
    MockWs66i,
)

from tests.common import MockConfigEntry

ZONE_1_ID = "media_player.zone_11"


async def test_cannot_connect(menuai: menuai) -> None:
    """Test connection error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=MOCK_OPTIONS
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.ws66i.get_ws66i",
        new=lambda *a: MockWs66i(fail_open=True),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        assert menuai.states.get(ZONE_1_ID) is None


async def test_cannot_connect_2(menuai: menuai) -> None:
    """Test connection error pt 2."""
    # Another way to test same case as test_cannot_connect
    ws66i = MockWs66i()
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=MOCK_DEFAULT_OPTIONS
    )
    config_entry.add_to_menuai(menuai)

    with patch.object(MockWs66i, "open", side_effect=ConnectionError):
        with patch(
            "menuai.components.ws66i.get_ws66i",
            new=lambda *a: ws66i,
        ):
            await menuai.config_entries.async_setup(config_entry.entry_id)
            await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        assert menuai.states.get(ZONE_1_ID) is None


async def test_unload_config_entry(menuai: menuai) -> None:
    """Test unloading config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, options=MOCK_OPTIONS
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.ws66i.get_ws66i",
        new=lambda *a: MockWs66i(),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.data[DOMAIN][config_entry.entry_id]

    with patch.object(MockWs66i, "close") as method_call:
        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert method_call.called

    assert not menuai.data[DOMAIN]
