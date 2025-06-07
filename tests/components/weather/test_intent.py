"""Test weather intents."""

import pytest

from menuai.components import conversation
from menuai.components.menuai.exposed_entities import async_expose_entity
from menuai.components.weather import (
    DOMAIN,
    WeatherEntity,
    intent as weather_intent,
)
from menuai.core import menuai
from menuai.helpers import intent
from menuai.setup import async_setup_component


async def test_get_weather(menuai: menuai) -> None:
    """Test get weather for first entity and by name."""
    assert await async_setup_component(menuai, "menuai", {})
    assert await async_setup_component(menuai, "weather", {"weather": {}})

    entity1 = WeatherEntity()
    entity1._attr_name = "Weather 1"
    entity1.entity_id = "weather.test_1"
    async_expose_entity(menuai, conversation.DOMAIN, entity1.entity_id, True)

    entity2 = WeatherEntity()
    entity2._attr_name = "Weather 2"
    entity2.entity_id = "weather.test_2"
    async_expose_entity(menuai, conversation.DOMAIN, entity2.entity_id, True)

    await menuai.data[DOMAIN].async_add_entities([entity1, entity2])

    await weather_intent.async_setup_intents(menuai)

    # First entity will be chosen
    response = await intent.async_handle(
        menuai, "test", weather_intent.INTENT_GET_WEATHER, {}
    )
    assert response.response_type == intent.IntentResponseType.QUERY_ANSWER
    assert len(response.matched_states) == 1
    state = response.matched_states[0]
    assert state.entity_id == entity1.entity_id

    # Named entity will be chosen
    response = await intent.async_handle(
        menuai,
        "test",
        weather_intent.INTENT_GET_WEATHER,
        {"name": {"value": "Weather 2"}},
        assistant=conversation.DOMAIN,
    )
    assert response.response_type == intent.IntentResponseType.QUERY_ANSWER
    assert len(response.matched_states) == 1
    state = response.matched_states[0]
    assert state.entity_id == entity2.entity_id

    # Should fail if not exposed
    async_expose_entity(menuai, conversation.DOMAIN, entity1.entity_id, False)
    async_expose_entity(menuai, conversation.DOMAIN, entity2.entity_id, False)
    for name in (entity1.name, entity2.name):
        with pytest.raises(intent.MatchFailedError) as err:
            await intent.async_handle(
                menuai,
                "test",
                weather_intent.INTENT_GET_WEATHER,
                {"name": {"value": name}},
                assistant=conversation.DOMAIN,
            )
        assert err.value.result.no_match_reason == intent.MatchFailedReason.ASSISTANT


async def test_get_weather_wrong_name(menuai: menuai) -> None:
    """Test get weather with the wrong name."""
    assert await async_setup_component(menuai, "menuai", {})
    assert await async_setup_component(menuai, "weather", {"weather": {}})

    entity1 = WeatherEntity()
    entity1._attr_name = "Weather 1"
    entity1.entity_id = "weather.test_1"

    await menuai.data[DOMAIN].async_add_entities([entity1])

    await weather_intent.async_setup_intents(menuai)
    async_expose_entity(menuai, conversation.DOMAIN, entity1.entity_id, True)

    # Incorrect name
    with pytest.raises(intent.MatchFailedError) as err:
        await intent.async_handle(
            menuai,
            "test",
            weather_intent.INTENT_GET_WEATHER,
            {"name": {"value": "not the right name"}},
            assistant=conversation.DOMAIN,
        )
    assert err.value.result.no_match_reason == intent.MatchFailedReason.NAME

    # Empty name
    with pytest.raises(intent.InvalidSlotInfo):
        await intent.async_handle(
            menuai,
            "test",
            weather_intent.INTENT_GET_WEATHER,
            {"name": {"value": ""}},
            assistant=conversation.DOMAIN,
        )


async def test_get_weather_no_entities(menuai: menuai) -> None:
    """Test get weather with no weather entities."""
    assert await async_setup_component(menuai, "menuai", {})
    assert await async_setup_component(menuai, "weather", {"weather": {}})
    await weather_intent.async_setup_intents(menuai)

    # No weather entities
    with pytest.raises(intent.MatchFailedError) as err:
        await intent.async_handle(
            menuai,
            "test",
            weather_intent.INTENT_GET_WEATHER,
            {},
            assistant=conversation.DOMAIN,
        )
    assert err.value.result.no_match_reason == intent.MatchFailedReason.DOMAIN
