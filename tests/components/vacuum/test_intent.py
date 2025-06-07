"""The tests for the vacuum platform."""

from menuai.components.vacuum import (
    DOMAIN,
    SERVICE_RETURN_TO_BASE,
    SERVICE_START,
    intent as vacuum_intent,
)
from menuai.const import STATE_IDLE
from menuai.core import menuai
from menuai.helpers import intent

from tests.common import async_mock_service


async def test_start_vacuum_intent(menuai: menuai) -> None:
    """Test menuaiTurnOn intent for vacuums."""
    await vacuum_intent.async_setup_intents(menuai)

    entity_id = f"{DOMAIN}.test_vacuum"
    menuai.states.async_set(entity_id, STATE_IDLE)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_START)

    response = await intent.async_handle(
        menuai,
        "test",
        vacuum_intent.INTENT_VACUUM_START,
        {"name": {"value": "test vacuum"}},
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_START
    assert call.data == {"entity_id": entity_id}


async def test_start_vacuum_without_name(menuai: menuai) -> None:
    """Test starting a vacuum without specifying the name."""
    await vacuum_intent.async_setup_intents(menuai)

    entity_id = f"{DOMAIN}.test_vacuum"
    menuai.states.async_set(entity_id, STATE_IDLE)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_START)

    response = await intent.async_handle(
        menuai, "test", vacuum_intent.INTENT_VACUUM_START, {}
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_START
    assert call.data == {"entity_id": entity_id}


async def test_stop_vacuum_intent(menuai: menuai) -> None:
    """Test menuaiTurnOff intent for vacuums."""
    await vacuum_intent.async_setup_intents(menuai)

    entity_id = f"{DOMAIN}.test_vacuum"
    menuai.states.async_set(entity_id, STATE_IDLE)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_RETURN_TO_BASE)

    response = await intent.async_handle(
        menuai,
        "test",
        vacuum_intent.INTENT_VACUUM_RETURN_TO_BASE,
        {"name": {"value": "test vacuum"}},
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_RETURN_TO_BASE
    assert call.data == {"entity_id": entity_id}


async def test_stop_vacuum_without_name(menuai: menuai) -> None:
    """Test stopping a vacuum without specifying the name."""
    await vacuum_intent.async_setup_intents(menuai)

    entity_id = f"{DOMAIN}.test_vacuum"
    menuai.states.async_set(entity_id, STATE_IDLE)
    calls = async_mock_service(menuai, DOMAIN, SERVICE_RETURN_TO_BASE)

    response = await intent.async_handle(
        menuai, "test", vacuum_intent.INTENT_VACUUM_RETURN_TO_BASE, {}
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_RETURN_TO_BASE
    assert call.data == {"entity_id": entity_id}
