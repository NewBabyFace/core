"""Tests for the Tankerkoening integration."""

from __future__ import annotations

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("setup_integration")
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
    assert result == snapshot(exclude=props("created_at", "modified_at"))
