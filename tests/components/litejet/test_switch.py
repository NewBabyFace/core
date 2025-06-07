"""The tests for the litejet component."""

from menuai.components import switch
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai

from . import async_init_integration

ENTITY_SWITCH = "switch.mock_switch_1"
ENTITY_SWITCH_NUMBER = 1
ENTITY_OTHER_SWITCH = "switch.mock_switch_2"
ENTITY_OTHER_SWITCH_NUMBER = 2


async def test_on_off(menuai: menuai, mock_litejet) -> None:
    """Test turning the switch on and off."""

    await async_init_integration(menuai, use_switch=True)

    assert menuai.states.get(ENTITY_SWITCH).state == STATE_OFF
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_OFF

    assert not switch.is_on(menuai, ENTITY_SWITCH)

    await menuai.services.async_call(
        switch.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_SWITCH}, blocking=True
    )
    mock_litejet.press_switch.assert_called_with(ENTITY_SWITCH_NUMBER)

    await menuai.services.async_call(
        switch.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_SWITCH}, blocking=True
    )
    mock_litejet.release_switch.assert_called_with(ENTITY_SWITCH_NUMBER)


async def test_pressed_event(menuai: menuai, mock_litejet) -> None:
    """Test handling an event from LiteJet."""

    await async_init_integration(menuai, use_switch=True)

    # Switch 1
    mock_litejet.switch_pressed_callbacks[ENTITY_SWITCH_NUMBER]()
    await menuai.async_block_till_done()

    assert switch.is_on(menuai, ENTITY_SWITCH)
    assert not switch.is_on(menuai, ENTITY_OTHER_SWITCH)
    assert menuai.states.get(ENTITY_SWITCH).state == STATE_ON
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_OFF

    # Switch 2
    mock_litejet.switch_pressed_callbacks[ENTITY_OTHER_SWITCH_NUMBER]()
    await menuai.async_block_till_done()

    assert switch.is_on(menuai, ENTITY_OTHER_SWITCH)
    assert switch.is_on(menuai, ENTITY_SWITCH)
    assert menuai.states.get(ENTITY_SWITCH).state == STATE_ON
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_ON


async def test_released_event(menuai: menuai, mock_litejet) -> None:
    """Test handling an event from LiteJet."""

    await async_init_integration(menuai, use_switch=True)

    # Initial state is on.
    mock_litejet.switch_pressed_callbacks[ENTITY_OTHER_SWITCH_NUMBER]()
    await menuai.async_block_till_done()

    assert switch.is_on(menuai, ENTITY_OTHER_SWITCH)

    # Event indicates it is off now.
    mock_litejet.switch_released_callbacks[ENTITY_OTHER_SWITCH_NUMBER]()
    await menuai.async_block_till_done()

    assert not switch.is_on(menuai, ENTITY_OTHER_SWITCH)
    assert not switch.is_on(menuai, ENTITY_SWITCH)
    assert menuai.states.get(ENTITY_SWITCH).state == STATE_OFF
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_OFF


async def test_connected_event(menuai: menuai, mock_litejet) -> None:
    """Test handling an event from LiteJet."""

    await async_init_integration(menuai, use_switch=True)

    # Initial state is available.
    assert menuai.states.get(ENTITY_SWITCH).state == STATE_OFF
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_OFF

    # Event indicates it is disconnected now.
    mock_litejet.connected_changed(False, "test")
    await menuai.async_block_till_done()

    assert menuai.states.get(ENTITY_SWITCH).state == STATE_UNAVAILABLE
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_UNAVAILABLE

    # Event indicates it is connected now.
    mock_litejet.connected_changed(True, None)
    await menuai.async_block_till_done()

    assert menuai.states.get(ENTITY_SWITCH).state == STATE_OFF
    assert menuai.states.get(ENTITY_OTHER_SWITCH).state == STATE_OFF
