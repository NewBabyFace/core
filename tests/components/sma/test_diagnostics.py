"""Test the SMA diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_get_config_entry_diagnostics(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test if get_config_entry_diagnostics returns the correct data."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )
    assert diagnostics == snapshot(
        exclude=props("created_at", "modified_at", "entry_id")
    )
