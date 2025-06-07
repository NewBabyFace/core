"""Test Blink diagnostics."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

YAML_CONFIG = {"username": "test-user", "password": "test-password"}


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_blink_api: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test config entry diagnostics."""

    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )

    assert result == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
