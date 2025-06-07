"""Test Ring diagnostics."""

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_ring_client,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Ring diagnostics."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, mock_config_entry)
    assert diag == snapshot
