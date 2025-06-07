"""Test AirVisual Pro diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    config_entry,
    menuai_client: ClientSessionGenerator,
    setup_airvisual_pro,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
