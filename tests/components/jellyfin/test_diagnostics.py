"""Test Jellyfin diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    init_integration: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""
    data = await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)

    assert data["entry"]["data"]["client_device_id"] == init_integration.entry_id
    data["entry"]["data"]["client_device_id"] = "entry-id"

    assert data == snapshot
