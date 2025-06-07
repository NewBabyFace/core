"""Tests for the Tankerkoening integration."""

from __future__ import annotations

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_ON
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("setup_integration")
async def test_binary_sensor(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tankerkoenig binary sensors."""

    state = menuai.states.get("binary_sensor.station_somewhere_street_1_status")
    assert state
    assert state.state == STATE_ON
    assert state.attributes == snapshot
