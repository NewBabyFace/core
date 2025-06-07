"""Test GeoNet NZ Quakes diagnostics."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2024-09-05 15:00:00")
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
) -> None:
    """Test config entry diagnostics."""
    with patch("aio_geojson_client.feed.GeoJsonFeed.update") as mock_feed_update:
        mock_feed_update.return_value = "OK", []

        config_entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        assert result == snapshot
