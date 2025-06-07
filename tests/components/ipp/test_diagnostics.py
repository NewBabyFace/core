"""Tests for the diagnostics data provided by the Internet Printing Protocol (IPP) integration."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2019-11-11 09:10:32+00:00")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics for config entry."""
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )
