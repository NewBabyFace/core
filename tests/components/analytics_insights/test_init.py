"""Test the MenuAI analytics init module."""

from __future__ import annotations

from unittest.mock import AsyncMock

from menuai.components.analytics_insights.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_entry(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test load and unload entry."""
    await setup_integration(menuai, mock_config_entry)
    entry = menuai.config_entries.async_entries(DOMAIN)[0]

    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
