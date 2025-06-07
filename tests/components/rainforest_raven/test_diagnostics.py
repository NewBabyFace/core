"""Test the Rainforest Eagle diagnostics."""

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import create_mock_entry

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.fixture
async def mock_entry_no_meters(
    menuai: menuai, mock_device: AsyncMock
) -> MockConfigEntry:
    """Mock a RAVEn config entry with no meters."""
    mock_entry = create_mock_entry(True)
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()
    return mock_entry


async def test_entry_diagnostics_no_meters(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_entry_no_meters: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test RAVEn diagnostics before the coordinator has updated."""
    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_entry_no_meters
    )
    assert result == snapshot(exclude=props("created_at", "modified_at"))


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test RAVEn diagnostics."""
    result = await get_diagnostics_for_config_entry(menuai, menuai_client, mock_entry)

    assert result == snapshot(exclude=props("created_at", "modified_at"))
