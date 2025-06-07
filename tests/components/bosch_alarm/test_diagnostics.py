"""Test the Bosch Alarm diagnostics."""

from typing import Any
from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_panel: AsyncMock,
    area: AsyncMock,
    model_name: str,
    serial_number: str,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    config_flow_data: dict[str, Any],
) -> None:
    """Test generating diagnostics for bosch alarm."""
    await setup_integration(menuai, mock_config_entry)

    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, mock_config_entry)
    assert diag == snapshot
