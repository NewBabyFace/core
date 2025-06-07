"""Tests for the steamist sensos."""

from __future__ import annotations

from menuai.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature, UnitOfTime
from menuai.core import menuai

from . import (
    MOCK_ASYNC_GET_STATUS_ACTIVE,
    MOCK_ASYNC_GET_STATUS_INACTIVE,
    _async_setup_entry_with_status,
)


async def test_steam_active(menuai: menuai) -> None:
    """Test that the sensors are setup with the expected values when steam is active."""
    await _async_setup_entry_with_status(menuai, MOCK_ASYNC_GET_STATUS_ACTIVE)
    state = menuai.states.get("sensor.steam_temperature")
    assert round(float(state.state)) == 39
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    state = menuai.states.get("sensor.steam_minutes_remain")
    assert state.state == "14"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTime.MINUTES


async def test_steam_inactive(menuai: menuai) -> None:
    """Test that the sensors are setup with the expected values when steam is not active."""
    await _async_setup_entry_with_status(menuai, MOCK_ASYNC_GET_STATUS_INACTIVE)
    state = menuai.states.get("sensor.steam_temperature")
    assert round(float(state.state)) == 21
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    state = menuai.states.get("sensor.steam_minutes_remain")
    assert state.state == "0"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTime.MINUTES
