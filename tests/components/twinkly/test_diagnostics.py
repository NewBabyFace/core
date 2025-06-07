"""Tests for the diagnostics of the twinkly component."""

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_twinkly_client")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    await setup_integration(menuai, mock_config_entry)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
