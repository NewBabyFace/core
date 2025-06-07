"""Tests for Vodafone Station diagnostics platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await setup_integration(menuai, mock_config_entry)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    ) == snapshot(
        exclude=props(
            "entry_id",
            "created_at",
            "modified_at",
        )
    )
