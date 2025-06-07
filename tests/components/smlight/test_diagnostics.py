"""Test SMLIGHT diagnostics."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.smlight.const import DOMAIN
from menuai.core import menuai

from .conftest import setup_integration

from tests.common import MockConfigEntry, async_load_fixture
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    mock_smlight_client.get.return_value = await async_load_fixture(
        menuai, "logs.txt", DOMAIN
    )
    entry = await setup_integration(menuai, mock_config_entry)

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    assert result == snapshot
