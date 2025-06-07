"""Tests for the light intents."""

from menuai.components import light
from menuai.components.light import ATTR_SUPPORTED_COLOR_MODES, ColorMode, intent
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.helpers.intent import async_handle

from tests.common import async_mock_service


async def test_intent_set_color(menuai: menuai) -> None:
    """Test the set color intent."""
    menuai.states.async_set(
        "light.hello_2", "off", {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.HS]}
    )
    menuai.states.async_set("switch.hello", "off")
    calls = async_mock_service(menuai, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(menuai)

    await async_handle(
        menuai,
        "test",
        intent.INTENT_SET,
        {"name": {"value": "Hello 2"}, "color": {"value": "blue"}},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "light.hello_2"
    assert call.data.get(light.ATTR_RGB_COLOR) == (0, 0, 255)


async def test_intent_set_color_and_brightness(menuai: menuai) -> None:
    """Test the set color intent."""
    menuai.states.async_set(
        "light.hello_2", "off", {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.HS]}
    )
    menuai.states.async_set("switch.hello", "off")
    calls = async_mock_service(menuai, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(menuai)

    await async_handle(
        menuai,
        "test",
        intent.INTENT_SET,
        {
            "name": {"value": "Hello 2"},
            "color": {"value": "blue"},
            "brightness": {"value": "20"},
        },
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "light.hello_2"
    assert call.data.get(light.ATTR_RGB_COLOR) == (0, 0, 255)
    assert call.data.get(light.ATTR_BRIGHTNESS_PCT) == 20


async def test_intent_set_temperature(menuai: menuai) -> None:
    """Test setting the color temperature in kevin via intent."""
    menuai.states.async_set(
        "light.test", "off", {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP]}
    )
    calls = async_mock_service(menuai, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(menuai)

    await async_handle(
        menuai,
        "test",
        intent.INTENT_SET,
        {
            "name": {"value": "Test"},
            "temperature": {"value": 2000},
        },
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "light.test"
    assert call.data.get(light.ATTR_COLOR_TEMP_KELVIN) == 2000
