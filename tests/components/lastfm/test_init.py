"""Test LastFM component setup process."""

from __future__ import annotations

from menuai.components.lastfm.const import DOMAIN
from menuai.core import menuai

from . import MockUser
from .conftest import ComponentSetup

from tests.common import MockConfigEntry


async def test_load_unload_entry(
    menuai: menuai,
    setup_integration: ComponentSetup,
    config_entry: MockConfigEntry,
    default_user: MockUser,
) -> None:
    """Test load and unload entry."""
    await setup_integration(config_entry, default_user)
    entry = menuai.config_entries.async_entries(DOMAIN)[0]

    state = menuai.states.get("sensor.lastfm_testaccount1")
    assert state

    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.lastfm_testaccount1")
    assert not state
