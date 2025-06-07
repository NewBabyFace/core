"""Tests Starlink integration init/unload."""

from menuai.components.starlink.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_IP_ADDRESS
from menuai.core import menuai

from .patchers import (
    HISTORY_STATS_SUCCESS_PATCHER,
    LOCATION_DATA_SUCCESS_PATCHER,
    SLEEP_DATA_SUCCESS_PATCHER,
    STATUS_DATA_SUCCESS_PATCHER,
)

from tests.common import MockConfigEntry


async def test_successful_entry(menuai: menuai) -> None:
    """Test configuring Starlink."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IP_ADDRESS: "1.2.3.4:0000"},
    )

    with (
        STATUS_DATA_SUCCESS_PATCHER,
        LOCATION_DATA_SUCCESS_PATCHER,
        SLEEP_DATA_SUCCESS_PATCHER,
        HISTORY_STATS_SUCCESS_PATCHER,
    ):
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert entry.runtime_data
        assert entry.runtime_data.data
        assert entry.state is ConfigEntryState.LOADED


async def test_unload_entry(menuai: menuai) -> None:
    """Test removing Starlink."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IP_ADDRESS: "1.2.3.4:0000"},
    )

    with (
        STATUS_DATA_SUCCESS_PATCHER,
        LOCATION_DATA_SUCCESS_PATCHER,
        SLEEP_DATA_SUCCESS_PATCHER,
        HISTORY_STATS_SUCCESS_PATCHER,
    ):
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert await menuai.config_entries.async_unload(entry.entry_id)
        await menuai.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED
