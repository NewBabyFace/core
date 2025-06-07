"""The tests for the demo number component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
    NumberMode,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_MODE, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.setup import async_setup_component

ENTITY_VOLUME = "number.volume"
ENTITY_PWM = "number.pwm_1"
ENTITY_LARGE_RANGE = "number.large_range"
ENTITY_SMALL_RANGE = "number.small_range"


@pytest.fixture
def number_only() -> Generator[None]:
    """Enable only the number platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.NUMBER],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_number(menuai: menuai, number_only: None) -> None:
    """Initialize setup demo Number entity."""
    assert await async_setup_component(
        menuai, NUMBER_DOMAIN, {"number": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"


def test_default_setup_params(menuai: menuai) -> None:
    """Test the setup with default parameters."""
    state = menuai.states.get(ENTITY_VOLUME)
    assert state.attributes.get(ATTR_MIN) == 0.0
    assert state.attributes.get(ATTR_MAX) == 100.0
    assert state.attributes.get(ATTR_STEP) == 1.0
    assert state.attributes.get(ATTR_MODE) == NumberMode.SLIDER

    state = menuai.states.get(ENTITY_PWM)
    assert state.attributes.get(ATTR_MIN) == 0.0
    assert state.attributes.get(ATTR_MAX) == 1.0
    assert state.attributes.get(ATTR_STEP) == 0.01
    assert state.attributes.get(ATTR_MODE) == NumberMode.BOX

    state = menuai.states.get(ENTITY_LARGE_RANGE)
    assert state.attributes.get(ATTR_MIN) == 1.0
    assert state.attributes.get(ATTR_MAX) == 1000.0
    assert state.attributes.get(ATTR_STEP) == 1.0
    assert state.attributes.get(ATTR_MODE) == NumberMode.AUTO

    state = menuai.states.get(ENTITY_SMALL_RANGE)
    assert state.attributes.get(ATTR_MIN) == 1.0
    assert state.attributes.get(ATTR_MAX) == 255.0
    assert state.attributes.get(ATTR_STEP) == 1.0
    assert state.attributes.get(ATTR_MODE) == NumberMode.AUTO


async def test_set_value_bad_attr(menuai: menuai) -> None:
    """Test setting the value without required attribute."""
    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_VALUE: None, ATTR_ENTITY_ID: ENTITY_VOLUME},
            blocking=True,
        )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"


async def test_set_value_bad_range(menuai: menuai) -> None:
    """Test setting the value out of range."""
    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_VALUE: 1024, ATTR_ENTITY_ID: ENTITY_VOLUME},
            blocking=True,
        )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"


async def test_set_set_value(menuai: menuai) -> None:
    """Test the setting of the value."""
    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "42.0"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_VALUE: 23, ATTR_ENTITY_ID: ENTITY_VOLUME},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_VOLUME)
    assert state.state == "23.0"
