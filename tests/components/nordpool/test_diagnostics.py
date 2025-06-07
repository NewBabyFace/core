"""Test Nord Pool diagnostics."""

from __future__ import annotations

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2024-11-05T10:00:00+00:00")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    load_int: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, load_int) == snapshot
    )
