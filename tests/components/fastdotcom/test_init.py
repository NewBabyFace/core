"""Test for Sensibo component Init."""

from __future__ import annotations

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory

from menuai.components.fastdotcom.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STARTED, STATE_UNKNOWN
from menuai.core import CoreState, menuai

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload an entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UNIQUE_TEST_ID",
        title=DEFAULT_NAME,
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.fastdotcom.coordinator.fast_com", return_value=5.0
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_delayed_speedtest_during_startup(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test delayed speedtest during startup."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UNIQUE_TEST_ID",
        title=DEFAULT_NAME,
    )
    config_entry.add_to_menuai(menuai)

    original_state = menuai.state
    menuai.set_state(CoreState.starting)
    with patch("menuai.components.fastdotcom.coordinator.fast_com"):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
    menuai.set_state(original_state)

    assert config_entry.state is ConfigEntryState.LOADED
    state = menuai.states.get("sensor.fast_com_download")
    # Assert state is Unknown as fast.com isn't starting until HA has started
    assert state.state is STATE_UNKNOWN

    with patch(
        "menuai.components.fastdotcom.coordinator.fast_com", return_value=5.0
    ):
        menuai.bus.async_fire(EVENT_menuai_STARTED)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.fast_com_download")
    assert state is not None
    assert state.state == "5.0"

    assert config_entry.state is ConfigEntryState.LOADED
