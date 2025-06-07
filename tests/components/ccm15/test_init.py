"""Tests for the ccm15 component."""

import pytest

from menuai.components.ccm15.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("ccm15_device")
async def test_load_unload(menuai: menuai) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.1.1.1",
        data={
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 80,
        },
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
