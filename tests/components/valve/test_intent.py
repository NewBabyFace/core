"""The tests for the valve platform."""

from menuai.components.valve import (
    ATTR_CURRENT_POSITION,
    DOMAIN,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_SET_VALVE_POSITION,
    ValveState,
)
from menuai.core import menuai
from menuai.helpers import intent
from menuai.setup import async_setup_component

from tests.common import async_mock_service


async def test_open_valve_intent(menuai: menuai) -> None:
    """Test menuaiTurnOn intent for valves."""
    assert await async_setup_component(menuai, "intent", {})

    entity_id = f"{DOMAIN}.test_valve"
    menuai.states.async_set(entity_id, ValveState.CLOSED)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_OPEN_VALVE)

    response = await intent.async_handle(
        menuai, "test", intent.INTENT_TURN_ON, {"name": {"value": "test valve"}}
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_OPEN_VALVE
    assert call.data == {"entity_id": entity_id}


async def test_close_valve_intent(menuai: menuai) -> None:
    """Test menuaiTurnOff intent for valves."""
    assert await async_setup_component(menuai, "intent", {})

    entity_id = f"{DOMAIN}.test_valve"
    menuai.states.async_set(entity_id, ValveState.OPEN)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_CLOSE_VALVE)

    response = await intent.async_handle(
        menuai, "test", intent.INTENT_TURN_OFF, {"name": {"value": "test valve"}}
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_CLOSE_VALVE
    assert call.data == {"entity_id": entity_id}


async def test_set_valve_position(menuai: menuai) -> None:
    """Test menuaiSetPosition intent for valves."""
    assert await async_setup_component(menuai, "intent", {})

    entity_id = f"{DOMAIN}.test_valve"
    menuai.states.async_set(
        entity_id, ValveState.CLOSED, attributes={ATTR_CURRENT_POSITION: 0}
    )
    calls = async_mock_service(menuai, DOMAIN, SERVICE_SET_VALVE_POSITION)

    response = await intent.async_handle(
        menuai,
        "test",
        intent.INTENT_SET_POSITION,
        {"name": {"value": "test valve"}, "position": {"value": 50}},
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_SET_VALVE_POSITION
    assert call.data == {"entity_id": entity_id, "position": 50}
