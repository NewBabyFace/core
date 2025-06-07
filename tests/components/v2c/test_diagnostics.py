"""Test V2C diagnostics."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from . import init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    mock_config_entry: ConfigEntry,
    mock_v2c_client: AsyncMock,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""

    await init_integration(menuai, mock_config_entry)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    ) == snapshot(exclude=props("created_at", "modified_at"))
