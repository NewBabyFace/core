"""Test the Advantage Air Diagnostics."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import add_mock_config

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_select_async_setup_entry(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_get: AsyncMock,
) -> None:
    """Test select platform."""

    entry = await add_mock_config(menuai)
    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)
    assert diag == snapshot
