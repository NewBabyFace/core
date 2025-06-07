"""Test madVR diagnostics."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.const import Platform
from menuai.core import menuai

from . import setup_integration
from .conftest import get_update_callback

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.parametrize(
    ("positive_payload"),
    [
        {"is_on": True},
    ],
)
async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_madvr_client: AsyncMock,
    snapshot: SnapshotAssertion,
    positive_payload: dict,
) -> None:
    """Test config entry diagnostics."""
    with patch("menuai.components.madvr.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    update_callback = get_update_callback(mock_madvr_client)

    # Add data to test storing diagnostic data
    update_callback(positive_payload)
    await menuai.async_block_till_done()

    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )

    assert result == snapshot(exclude=props("created_at", "modified_at"))
