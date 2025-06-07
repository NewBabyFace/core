"""Tests for diagnostics data."""

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.const import CONF_USERNAME
from menuai.core import menuai

from .const import VALID_ENTRY_DATA_CLOUD, VALID_ENTRY_DATA_SELF_HOSTED

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.parametrize(
    "mock_config_entry_data",
    [VALID_ENTRY_DATA_CLOUD, VALID_ENTRY_DATA_SELF_HOSTED],
    ids=lambda data: data[CONF_USERNAME],
)
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, init_integration
    ) == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
