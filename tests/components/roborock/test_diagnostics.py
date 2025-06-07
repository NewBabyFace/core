"""Tests for the diagnostics data provided by the Roborock integration."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics for config entry."""
    result = await get_diagnostics_for_config_entry(menuai, menuai_client, setup_entry)

    assert isinstance(result, dict)
    assert result == snapshot(exclude=props("Nonce"))
