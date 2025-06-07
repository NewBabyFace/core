"""Tests for the diagnostics data provided by LG webOS TV."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import setup_webostv

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    client,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    entry = await setup_webostv(menuai)
    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot(
        exclude=props("created_at", "modified_at", "entry_id")
    )
