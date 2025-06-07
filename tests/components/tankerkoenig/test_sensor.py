"""Tests for the Tankerkoening integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.tankerkoenig import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import PRICES_MISSING_FUELTYPE, STATION_MISSING_FUELTYPE

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("setup_integration")
async def test_sensor(
    menuai: menuai,
    tankerkoenig: AsyncMock,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tankerkoenig sensors."""

    state = menuai.states.get("sensor.station_somewhere_street_1_super_e10")
    assert state
    assert state.state == "1.659"
    assert state.attributes == snapshot

    state = menuai.states.get("sensor.station_somewhere_street_1_super")
    assert state
    assert state.state == "1.719"
    assert state.attributes == snapshot

    state = menuai.states.get("sensor.station_somewhere_street_1_diesel")
    assert state
    assert state.state == "1.659"
    assert state.attributes == snapshot


async def test_sensor_missing_fueltype(
    menuai: menuai,
    tankerkoenig: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test the tankerkoenig sensors."""
    tankerkoenig.station_details.return_value = STATION_MISSING_FUELTYPE
    tankerkoenig.prices.return_value = PRICES_MISSING_FUELTYPE

    config_entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.station_somewhere_street_1_super_e10")
    assert state

    state = menuai.states.get("sensor.station_somewhere_street_1_super")
    assert state

    state = menuai.states.get("sensor.station_somewhere_street_1_diesel")
    assert not state
