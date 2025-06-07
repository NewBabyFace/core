"""Tests for the One-Time Password (OTP) Sensors."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_pyotp")
async def test_setup(
    menuai: menuai,
    otp_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup of ista EcoTrend sensor platform."""

    otp_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(otp_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.otp_sensor") == snapshot
