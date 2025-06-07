"""Test for Trafikverket Ferry component Init."""

from __future__ import annotations

from unittest.mock import patch

from pytrafikverket.models import FerryStopModel

from menuai.components.trafikverket_ferry.const import DOMAIN
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.core import menuai

from . import ENTRY_CONFIG

from tests.common import MockConfigEntry


async def test_setup_entry(
    menuai: menuai, get_ferries: list[FerryStopModel]
) -> None:
    """Test setup entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        entry_id="1",
        unique_id="123",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.trafikverket_ferry.coordinator.TrafikverketFerry.async_get_next_ferry_stops",
        return_value=get_ferries,
    ) as mock_tvt_ferry:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert len(mock_tvt_ferry.mock_calls) == 1


async def test_unload_entry(
    menuai: menuai, get_ferries: list[FerryStopModel]
) -> None:
    """Test unload an entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        entry_id="1",
        unique_id="321",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.trafikverket_ferry.coordinator.TrafikverketFerry.async_get_next_ferry_stops",
        return_value=get_ferries,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
