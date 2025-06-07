"""Tests for the diagnostics data provided by the Roku integration."""

from rokuecp import Device as RokuDevice
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_device: RokuDevice,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics for config entry."""
    mock_device.state.at = dt_util.parse_datetime("2023-08-15 17:00:00-00:00")

    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )
