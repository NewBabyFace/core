"""Tests for the diagnostics data provided by the Cambridge Audio integration."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_stream_magic_client: AsyncMock,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await setup_integration(menuai, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )
    assert result == snapshot
