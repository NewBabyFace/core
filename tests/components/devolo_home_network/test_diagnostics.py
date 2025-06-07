"""Tests for the devolo Home Network diagnostics."""

from __future__ import annotations

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import configure_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("mock_device")
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)
    assert result == snapshot(exclude=props("created_at", "modified_at"))
