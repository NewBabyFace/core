"""The tests for the cover platform."""

from typing import Any

import pytest

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    CoverState,
    intent as cover_intent,
)
from menuai.core import menuai
from menuai.helpers import intent
from menuai.setup import async_setup_component

from tests.common import async_mock_service


@pytest.mark.parametrize(
    ("slots"),
    [
        ({"name": {"value": "garage door"}}),
        ({"device_class": {"value": "garage"}}),
    ],
)
async def test_open_cover_intent(menuai: menuai, slots: dict[str, Any]) -> None:
    """Test menuaiOpenCover intent."""
    await cover_intent.async_setup_intents(menuai)

    menuai.states.async_set(
        f"{DOMAIN}.garage_door",
        CoverState.CLOSED,
        attributes={"device_class": "garage"},
    )
    calls = async_mock_service(menuai, DOMAIN, SERVICE_OPEN_COVER)

    response = await intent.async_handle(
        menuai, "test", cover_intent.INTENT_OPEN_COVER, slots
    )
    await menuai.async_block_till_done()

    assert response.speech["plain"]["speech"] == "Opening garage door"
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_OPEN_COVER
    assert call.data == {"entity_id": f"{DOMAIN}.garage_door"}


@pytest.mark.parametrize(
    ("slots"),
    [
        ({"name": {"value": "garage door"}}),
        ({"device_class": {"value": "garage"}}),
    ],
)
async def test_close_cover_intent(menuai: menuai, slots: dict[str, Any]) -> None:
    """Test menuaiCloseCover intent."""
    await cover_intent.async_setup_intents(menuai)

    menuai.states.async_set(
        f"{DOMAIN}.garage_door", CoverState.OPEN, attributes={"device_class": "garage"}
    )
    calls = async_mock_service(menuai, DOMAIN, SERVICE_CLOSE_COVER)

    response = await intent.async_handle(
        menuai,
        "test",
        cover_intent.INTENT_CLOSE_COVER,
        slots,
    )
    await menuai.async_block_till_done()

    assert response.speech["plain"]["speech"] == "Closing garage door"
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_CLOSE_COVER
    assert call.data == {"entity_id": f"{DOMAIN}.garage_door"}


@pytest.mark.parametrize(
    ("slots"),
    [
        ({"name": {"value": "test cover"}, "position": {"value": 50}}),
        ({"device_class": {"value": "shade"}, "position": {"value": 50}}),
    ],
)
async def test_set_cover_position(menuai: menuai, slots: dict[str, Any]) -> None:
    """Test menuaiSetPosition intent for covers."""
    assert await async_setup_component(menuai, "intent", {})

    entity_id = f"{DOMAIN}.test_cover"
    menuai.states.async_set(
        entity_id,
        CoverState.CLOSED,
        attributes={ATTR_CURRENT_POSITION: 0, "device_class": "shade"},
    )
    calls = async_mock_service(menuai, DOMAIN, SERVICE_SET_COVER_POSITION)

    response = await intent.async_handle(
        menuai,
        "test",
        intent.INTENT_SET_POSITION,
        slots,
    )
    await menuai.async_block_till_done()

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == DOMAIN
    assert call.service == SERVICE_SET_COVER_POSITION
    assert call.data == {"entity_id": entity_id, "position": 50}
