"""Test the Nina init file."""

from typing import Any
from unittest.mock import patch

from pynina import ApiError

from menuai.components.nina.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import mocked_request_function

from tests.common import MockConfigEntry

ENTRY_DATA: dict[str, Any] = {
    "slots": 5,
    "headline_filter": ".*corona.*",
    "area_filter": ".*",
    "regions": {"083350000000": "Aach, Stadt"},
}


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the NINA integration in MenuAI."""

    with patch(
        "pynina.baseApi.BaseAPI._makeRequest",
        wraps=mocked_request_function,
    ):
        entry: MockConfigEntry = MockConfigEntry(
            domain=DOMAIN, title="NINA", data=ENTRY_DATA
        )
        entry.add_to_menuai(menuai)

        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()
        return entry


async def test_config_migration(menuai: menuai) -> None:
    """Test the migration to a new configuration layout."""

    old_entry_data: dict[str, Any] = {
        "slots": 5,
        "corona_filter": True,
        "regions": {"083350000000": "Aach, Stadt"},
    }

    old_conf_entry: MockConfigEntry = MockConfigEntry(
        domain=DOMAIN, title="NINA", data=old_entry_data
    )

    old_conf_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(old_conf_entry.entry_id)
    await menuai.async_block_till_done()

    assert dict(old_conf_entry.data) == ENTRY_DATA


async def test_config_entry_not_ready(menuai: menuai) -> None:
    """Test the configuration entry."""
    entry: MockConfigEntry = await init_integration(menuai)

    assert entry.state is ConfigEntryState.LOADED


async def test_sensors_connection_error(menuai: menuai) -> None:
    """Test the creation and values of the NINA sensors with no connected."""
    with patch(
        "pynina.baseApi.BaseAPI._makeRequest",
        side_effect=ApiError("Could not connect to Api"),
    ):
        conf_entry: MockConfigEntry = MockConfigEntry(
            domain=DOMAIN, title="NINA", data=ENTRY_DATA
        )

        conf_entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(conf_entry.entry_id)
        await menuai.async_block_till_done()

        assert conf_entry.state is ConfigEntryState.SETUP_RETRY
