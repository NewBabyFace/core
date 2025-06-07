"""Test the NZBGet config flow."""

from unittest.mock import patch

from pynzbgetapi import NZBGetAPIException
import pytest

from menuai.components.nzbget.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import ENTRY_CONFIG, _patch_version, init_integration

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("nzbget_api")
async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_raises_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    config_entry.add_to_menuai(menuai)

    with (
        _patch_version(),
        patch(
            "menuai.components.nzbget.coordinator.NZBGetAPI.status",
            side_effect=NZBGetAPIException(),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
