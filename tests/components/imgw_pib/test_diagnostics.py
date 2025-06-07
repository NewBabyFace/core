"""Test the IMGW-PIB diagnostics platform."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from . import init_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_imgw_pib_client: AsyncMock,
) -> None:
    """Test config entry diagnostics."""
    await init_integration(menuai, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )

    assert result == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
