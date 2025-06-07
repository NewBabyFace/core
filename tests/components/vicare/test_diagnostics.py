"""Test ViCare diagnostics."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_vicare_gas_boiler: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    diag = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_vicare_gas_boiler
    )

    assert diag == snapshot(exclude=props("created_at", "modified_at"))
