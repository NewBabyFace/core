"""Tests for the diagnostics data provided by the myuplink integration."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import paths

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    init_integration,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    ) == snapshot(
        exclude=paths(
            "config_entry_data.token.expires_at",
            "myuplink_test.entry_id",
            "config_entry_data.token.scope",
        )
    )
