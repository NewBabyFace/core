"""Tests for diagnostics data."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.parametrize(
    "device_fixture",
    [
        "HWE-P1",
        "HWE-SKT-11",
        "HWE-SKT-21",
        "HWE-WTR",
        "SDM230",
        "SDM630",
        "HWE-KWH1",
        "HWE-KWH3",
        "HWE-BAT",
    ],
)
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )
