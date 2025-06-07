"""Test Sensibo diagnostics."""

from __future__ import annotations

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    load_int: ConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    entry = load_int

    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert diag == snapshot(
        exclude=props("full_features", "created_at", "modified_at"),
    )
