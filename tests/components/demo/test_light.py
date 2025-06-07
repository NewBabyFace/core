"""The tests for the demo light component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.demo import DOMAIN
from menuai.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_XY_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_LIGHT = "light.bed_light"


@pytest.fixture
def light_only() -> Generator[None]:
    """Enable only the light platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.LIGHT],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, light_only: None) -> None:
    """Set up demo component."""
    assert await async_setup_component(
        menuai, LIGHT_DOMAIN, {LIGHT_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()


async def test_state_attributes(menuai: menuai) -> None:
    """Test light state attributes."""
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_LIGHT, ATTR_XY_COLOR: (0.4, 0.4), ATTR_BRIGHTNESS: 25},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_XY_COLOR) == (0.4, 0.4)
    assert state.attributes.get(ATTR_BRIGHTNESS) == 25
    assert state.attributes.get(ATTR_RGB_COLOR) == (255, 234, 164)
    assert state.attributes.get(ATTR_EFFECT) == "rainbow"

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ENTITY_LIGHT,
            ATTR_RGB_COLOR: (251, 253, 255),
        },
        blocking=True,
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.attributes.get(ATTR_RGB_COLOR) == (251, 253, 255)
    assert state.attributes.get(ATTR_XY_COLOR) == (0.319, 0.327)

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ENTITY_LIGHT,
            ATTR_EFFECT: "off",
            ATTR_COLOR_TEMP_KELVIN: 2500,
        },
        blocking=True,
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.attributes.get(ATTR_COLOR_TEMP_KELVIN) == 2500
    assert state.attributes.get(ATTR_MAX_COLOR_TEMP_KELVIN) == 6535
    assert state.attributes.get(ATTR_MIN_COLOR_TEMP_KELVIN) == 2000
    assert state.attributes.get(ATTR_EFFECT) == "off"

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: ENTITY_LIGHT,
            ATTR_BRIGHTNESS_PCT: 50,
            ATTR_COLOR_TEMP_KELVIN: 3000,
        },
        blocking=True,
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.attributes.get(ATTR_COLOR_TEMP_KELVIN) == 3000
    assert state.attributes.get(ATTR_BRIGHTNESS) == 128


async def test_turn_off(menuai: menuai) -> None:
    """Test light turn off method."""
    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_LIGHT}, blocking=True
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_LIGHT}, blocking=True
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.state == STATE_OFF


async def test_turn_off_without_entity_id(menuai: menuai) -> None:
    """Test light turn off all lights."""
    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: "all"}, blocking=True
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: "all"}, blocking=True
    )

    state = menuai.states.get(ENTITY_LIGHT)
    assert state.state == STATE_OFF
