"""Tests for the diagnostics data provided by the LaMetric integration."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )
