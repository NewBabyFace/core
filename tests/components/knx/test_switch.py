"""Test KNX switch."""

from menuai.components.knx.const import (
    CONF_RESPOND_TO_READ,
    CONF_STATE_ADDRESS,
    KNX_ADDRESS,
)
from menuai.components.knx.schema import SwitchSchema
from menuai.const import CONF_NAME, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai, State

from . import KnxEntityGenerator
from .conftest import KNXTestKit

from tests.common import mock_restore_cache


async def test_switch_simple(menuai: menuai, knx: KNXTestKit) -> None:
    """Test simple KNX switch."""
    await knx.setup_integration(
        {
            SwitchSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: "1/2/3",
            }
        }
    )

    # turn on switch
    await menuai.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.test"}, blocking=True
    )
    await knx.assert_write("1/2/3", True)

    # turn off switch
    await menuai.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.test"}, blocking=True
    )
    await knx.assert_write("1/2/3", False)

    # receive ON telegram
    await knx.receive_write("1/2/3", True)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_ON

    # receive OFF telegram
    await knx.receive_write("1/2/3", False)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_OFF

    # switch does not respond to read by default
    await knx.receive_read("1/2/3")
    await knx.assert_telegram_count(0)


async def test_switch_state(menuai: menuai, knx: KNXTestKit) -> None:
    """Test KNX switch with state_address."""
    _ADDRESS = "1/1/1"
    _STATE_ADDRESS = "2/2/2"

    await knx.setup_integration(
        {
            SwitchSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: _ADDRESS,
                CONF_STATE_ADDRESS: _STATE_ADDRESS,
            },
        }
    )

    # StateUpdater initialize state
    await knx.assert_read(_STATE_ADDRESS)
    await knx.receive_response(_STATE_ADDRESS, True)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_ON

    # receive OFF telegram at `address`
    await knx.receive_write(_ADDRESS, False)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_OFF

    # receive ON telegram at `address`
    await knx.receive_write(_ADDRESS, True)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_ON

    # receive OFF telegram at `state_address`
    await knx.receive_write(_STATE_ADDRESS, False)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_OFF

    # receive ON telegram at `state_address`
    await knx.receive_write(_STATE_ADDRESS, True)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_ON

    # turn off switch
    await menuai.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.test"}, blocking=True
    )
    await knx.assert_write(_ADDRESS, False)

    # turn on switch
    await menuai.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.test"}, blocking=True
    )
    await knx.assert_write(_ADDRESS, True)

    # switch does not respond to read by default
    await knx.receive_read(_ADDRESS)
    await knx.assert_telegram_count(0)


async def test_switch_restore_and_respond(menuai: menuai, knx) -> None:
    """Test restoring KNX switch state and respond to read."""
    _ADDRESS = "1/1/1"
    fake_state = State("switch.test", "on")
    mock_restore_cache(menuai, (fake_state,))

    await knx.setup_integration(
        {
            SwitchSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: _ADDRESS,
                CONF_RESPOND_TO_READ: True,
            },
        }
    )

    # restored state - doesn't send telegram
    state = menuai.states.get("switch.test")
    assert state.state == STATE_ON
    await knx.assert_telegram_count(0)

    # respond to restored state
    await knx.receive_read(_ADDRESS)
    await knx.assert_response(_ADDRESS, True)

    # turn off switch
    await menuai.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.test"}, blocking=True
    )
    await knx.assert_write(_ADDRESS, False)
    state = menuai.states.get("switch.test")
    assert state.state == STATE_OFF

    # respond to new state
    await knx.receive_read(_ADDRESS)
    await knx.assert_response(_ADDRESS, False)


async def test_switch_ui_create(
    menuai: menuai,
    knx: KNXTestKit,
    create_ui_entity: KnxEntityGenerator,
) -> None:
    """Test creating a switch."""
    await knx.setup_integration()
    await create_ui_entity(
        platform=Platform.SWITCH,
        entity_data={"name": "test"},
        knx_data={
            "ga_switch": {"write": "1/1/1", "state": "2/2/2"},
            "respond_to_read": True,
            "sync_state": True,
            "invert": False,
        },
    )
    # created entity sends read-request to KNX bus
    await knx.assert_read("2/2/2")
    await knx.receive_response("2/2/2", True)
    state = menuai.states.get("switch.test")
    assert state.state is STATE_ON


async def test_switch_ui_load(knx: KNXTestKit) -> None:
    """Test loading a switch from storage."""
    await knx.setup_integration(config_store_fixture="config_store_light_switch.json")

    await knx.assert_read("1/0/45", response=True, ignore_order=True)
    # unrelated light in config store
    await knx.assert_read("1/0/21", response=True, ignore_order=True)
    knx.assert_state(
        "switch.none_test",  # has_entity_name with unregistered device -> none_test
        STATE_ON,
    )
