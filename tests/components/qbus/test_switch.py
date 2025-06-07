"""Test Qbus switch entities."""

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from menuai.core import menuai

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient

_PAYLOAD_SWITCH_STATE_ON = '{"id":"UL10","properties":{"value":true},"type":"state"}'
_PAYLOAD_SWITCH_STATE_OFF = '{"id":"UL10","properties":{"value":false},"type":"state"}'
_PAYLOAD_SWITCH_SET_STATE_ON = (
    '{"id": "UL10", "type": "state", "properties": {"value": true}}'
)
_PAYLOAD_SWITCH_SET_STATE_OFF = (
    '{"id": "UL10", "type": "state", "properties": {"value": false}}'
)

_TOPIC_SWITCH_STATE = "cloudapp/QBUSMQTTGW/UL1/UL10/state"
_TOPIC_SWITCH_SET_STATE = "cloudapp/QBUSMQTTGW/UL1/UL10/setState"

_SWITCH_ENTITY_ID = "switch.living"


async def test_switch_turn_on_off(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    setup_integration: None,
) -> None:
    """Test turning on and off."""

    # Switch ON
    mqtt_mock.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: _SWITCH_ENTITY_ID},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        _TOPIC_SWITCH_SET_STATE, _PAYLOAD_SWITCH_SET_STATE_ON, 0, False
    )

    # Simulate response
    async_fire_mqtt_message(menuai, _TOPIC_SWITCH_STATE, _PAYLOAD_SWITCH_STATE_ON)
    await menuai.async_block_till_done()

    assert menuai.states.get(_SWITCH_ENTITY_ID).state == STATE_ON

    # Switch OFF
    mqtt_mock.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: _SWITCH_ENTITY_ID},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        _TOPIC_SWITCH_SET_STATE, _PAYLOAD_SWITCH_SET_STATE_OFF, 0, False
    )

    # Simulate response
    async_fire_mqtt_message(menuai, _TOPIC_SWITCH_STATE, _PAYLOAD_SWITCH_STATE_OFF)
    await menuai.async_block_till_done()

    assert menuai.states.get(_SWITCH_ENTITY_ID).state == STATE_OFF
