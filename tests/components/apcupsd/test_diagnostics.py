"""Test APCUPSd diagnostics reporting abilities."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import async_init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    entry = await async_init_integration(menuai)
    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot
