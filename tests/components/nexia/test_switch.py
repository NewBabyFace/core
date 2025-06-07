"""The switch tests for the nexia platform."""

from freezegun.api import FrozenDateTimeFactory

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    EVENT_menuai_STOP,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai

from .util import async_init_integration

from tests.common import async_fire_time_changed


async def test_hold_switch(menuai: menuai) -> None:
    """Test creation of the hold switch."""
    await async_init_integration(menuai)
    assert menuai.states.get("switch.nick_office_hold").state == STATE_ON


async def test_nexia_sensor_switch(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test NexiaRoomIQSensorSwitch."""
    await async_init_integration(menuai, house_fixture="sensors_xl1050_house.json")
    sw1_id = f"{Platform.SWITCH}.center_nativezone_include_center"
    sw1 = {ATTR_ENTITY_ID: sw1_id}
    sw2_id = f"{Platform.SWITCH}.center_nativezone_include_upstairs"
    sw2 = {ATTR_ENTITY_ID: sw2_id}

    # Switch starts out on.
    assert (entity_state := menuai.states.get(sw1_id)) is not None
    assert entity_state.state == STATE_ON

    # Turn switch off.
    await menuai.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_OFF, sw1, blocking=True)
    assert menuai.states.get(sw1_id).state == STATE_OFF

    # Turn switch back on.
    await menuai.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, sw1, blocking=True)
    assert menuai.states.get(sw1_id).state == STATE_ON

    # The other switch also starts out on.
    assert (entity_state := menuai.states.get(sw2_id)) is not None
    assert entity_state.state == STATE_ON

    # Turn both switches off, an invalid combination.
    await menuai.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_OFF, sw1, blocking=True)
    await menuai.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_OFF, sw2, blocking=True)
    assert menuai.states.get(sw1_id).state == STATE_OFF
    assert menuai.states.get(sw2_id).state == STATE_OFF

    # Wait for switches to revert to device status.
    freezer.tick(6)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert menuai.states.get(sw1_id).state == STATE_ON
    assert menuai.states.get(sw2_id).state == STATE_ON

    # Turn switch off.
    await menuai.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_OFF, sw2, blocking=True)
    assert menuai.states.get(sw2_id).state == STATE_OFF

    # Exercise shutdown path.
    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    assert menuai.states.get(sw2_id).state == STATE_ON
