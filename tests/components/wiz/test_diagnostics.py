"""Test WiZ diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import async_setup_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    _, entry = await async_setup_integration(menuai)

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot
