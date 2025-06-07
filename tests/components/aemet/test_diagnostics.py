"""Define tests for the AEMET OpenData diagnostics."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.aemet.const import DOMAIN
from menuai.core import menuai

from .util import async_init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2024-02-23T18:00:00+00:00")
async def test_config_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await async_init_integration(menuai)

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]

    with patch(
        "menuai.components.aemet.AEMET.raw_data",
        return_value={},
    ):
        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        assert result == snapshot(exclude=props("created_at", "modified_at"))
