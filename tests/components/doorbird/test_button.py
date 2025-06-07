"""Test DoorBird buttons."""

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai

from .conftest import DoorbirdMockerType


async def test_relay_button(
    menuai: menuai,
    doorbird_mocker: DoorbirdMockerType,
) -> None:
    """Test pressing a relay button."""
    doorbird_entry = await doorbird_mocker()
    relay_1_entity_id = "button.mydoorbird_relay_1"
    assert menuai.states.get(relay_1_entity_id).state == STATE_UNKNOWN
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: relay_1_entity_id}, blocking=True
    )
    assert menuai.states.get(relay_1_entity_id).state != STATE_UNKNOWN
    assert doorbird_entry.api.energize_relay.call_count == 1


async def test_ir_button(
    menuai: menuai,
    doorbird_mocker: DoorbirdMockerType,
) -> None:
    """Test pressing the IR button."""
    doorbird_entry = await doorbird_mocker()
    ir_entity_id = "button.mydoorbird_ir"
    assert menuai.states.get(ir_entity_id).state == STATE_UNKNOWN
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: ir_entity_id}, blocking=True
    )
    assert menuai.states.get(ir_entity_id).state != STATE_UNKNOWN
    assert doorbird_entry.api.turn_light_on.call_count == 1


async def test_reset_favorites_button(
    menuai: menuai,
    doorbird_mocker: DoorbirdMockerType,
) -> None:
    """Test pressing the reset favorites button."""
    doorbird_entry = await doorbird_mocker()
    reset_entity_id = "button.mydoorbird_reset_favorites"
    assert menuai.states.get(reset_entity_id).state == STATE_UNKNOWN
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: reset_entity_id}, blocking=True
    )
    assert menuai.states.get(reset_entity_id).state != STATE_UNKNOWN
    assert doorbird_entry.api.delete_favorite.call_count == 3
