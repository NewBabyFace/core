"""Test ONVIF diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import setup_onvif_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""

    entry, _, _ = await setup_onvif_integration(menuai)

    assert await get_diagnostics_for_config_entry(menuai, menuai_client, entry) == snapshot(
        exclude=props("created_at", "modified_at")
    )
