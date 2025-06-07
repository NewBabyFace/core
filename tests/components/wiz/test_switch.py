"""Tests for switch platform."""

import datetime

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.dt import utcnow

from . import FAKE_MAC, FAKE_SOCKET, async_push_update, async_setup_integration

from tests.common import async_fire_time_changed


async def test_switch_operation(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test switch operation."""
    switch, _ = await async_setup_integration(menuai, bulb_type=FAKE_SOCKET)
    entity_id = "switch.mock_title"
    assert entity_registry.async_get(entity_id).unique_id == FAKE_MAC
    assert menuai.states.get(entity_id).state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.turn_off.assert_called_once()

    await async_push_update(menuai, switch, {"mac": FAKE_MAC, "state": False})
    assert menuai.states.get(entity_id).state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.turn_on.assert_called_once()

    await async_push_update(menuai, switch, {"mac": FAKE_MAC, "state": True})
    assert menuai.states.get(entity_id).state == STATE_ON


async def test_update_fails(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test switch update fails when push updates are not working."""
    switch, _ = await async_setup_integration(menuai, bulb_type=FAKE_SOCKET)
    entity_id = "switch.mock_title"
    assert entity_registry.async_get(entity_id).unique_id == FAKE_MAC
    assert menuai.states.get(entity_id).state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    switch.turn_off.assert_called_once()

    switch.updateState.side_effect = OSError

    async_fire_time_changed(menuai, utcnow() + datetime.timedelta(seconds=15))
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_UNAVAILABLE
