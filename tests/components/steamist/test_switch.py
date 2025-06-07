"""Tests for the steamist switch."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import (
    MOCK_ASYNC_GET_STATUS_ACTIVE,
    MOCK_ASYNC_GET_STATUS_INACTIVE,
    _async_setup_entry_with_status,
)

from tests.common import async_fire_time_changed


async def test_steam_active(menuai: menuai) -> None:
    """Test that the switches are setup with the expected values when steam is active."""
    client, _ = await _async_setup_entry_with_status(menuai, MOCK_ASYNC_GET_STATUS_ACTIVE)
    assert len(menuai.states.async_all("switch")) == 1
    assert menuai.states.get("switch.steam_active").state == STATE_ON

    client.async_get_status = AsyncMock(return_value=MOCK_ASYNC_GET_STATUS_INACTIVE)
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {ATTR_ENTITY_ID: "switch.steam_active"},
        blocking=True,
    )
    client.async_turn_off_steam.assert_called_once()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=5))
    await menuai.async_block_till_done()
    assert menuai.states.get("switch.steam_active").state == STATE_OFF


async def test_steam_inactive(menuai: menuai) -> None:
    """Test that the switches are setup with the expected values when steam is not active."""
    client, _ = await _async_setup_entry_with_status(
        menuai, MOCK_ASYNC_GET_STATUS_INACTIVE
    )

    assert len(menuai.states.async_all("switch")) == 1
    assert menuai.states.get("switch.steam_active").state == STATE_OFF

    client.async_get_status = AsyncMock(return_value=MOCK_ASYNC_GET_STATUS_ACTIVE)
    await menuai.services.async_call(
        SWITCH_DOMAIN, "turn_on", {ATTR_ENTITY_ID: "switch.steam_active"}, blocking=True
    )
    client.async_turn_on_steam.assert_called_once()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=5))
    await menuai.async_block_till_done()
    assert menuai.states.get("switch.steam_active").state == STATE_ON
