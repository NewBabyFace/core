"""The tests for the demo humidifier component."""

from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.humidifier import (
    ATTR_ACTION,
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDITY,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    DOMAIN as HUMIDITY_DOMAIN,
    MODE_AWAY,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_MODE,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_DEHUMIDIFIER = "humidifier.dehumidifier"
ENTITY_HYGROSTAT = "humidifier.hygrostat"
ENTITY_HUMIDIFIER = "humidifier.humidifier"


@pytest.fixture
async def humidifier_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.HUMIDIFIER],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_humidifier(menuai: menuai, humidifier_only: None):
    """Initialize setup demo humidifier."""
    assert await async_setup_component(
        menuai, HUMIDITY_DOMAIN, {"humidifier": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_HUMIDITY) == 54.2
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 59.4
    assert state.attributes.get(ATTR_ACTION) == "drying"


def test_default_setup_params(menuai: menuai) -> None:
    """Test the setup with default parameters."""
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.attributes.get(ATTR_MIN_HUMIDITY) == 0
    assert state.attributes.get(ATTR_MAX_HUMIDITY) == 100


async def test_set_target_humidity_bad_attr(menuai: menuai) -> None:
    """Test setting the target humidity without required attribute."""
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.attributes.get(ATTR_HUMIDITY) == 54.2

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            HUMIDITY_DOMAIN,
            SERVICE_SET_HUMIDITY,
            {ATTR_HUMIDITY: None, ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
            blocking=True,
        )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.attributes.get(ATTR_HUMIDITY) == 54.2


async def test_set_target_humidity(menuai: menuai) -> None:
    """Test the setting of the target humidity."""
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.attributes.get(ATTR_HUMIDITY) == 54.2

    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_SET_HUMIDITY,
        {ATTR_HUMIDITY: 64, ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.attributes.get(ATTR_HUMIDITY) == 64


async def test_set_hold_mode_away(menuai: menuai) -> None:
    """Test setting the hold mode away."""
    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_SET_MODE,
        {ATTR_MODE: MODE_AWAY, ATTR_ENTITY_ID: ENTITY_HYGROSTAT},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_HYGROSTAT)
    assert state.attributes.get(ATTR_MODE) == MODE_AWAY


async def test_set_hold_mode_eco(menuai: menuai) -> None:
    """Test setting the hold mode eco."""
    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_SET_MODE,
        {ATTR_MODE: "eco", ATTR_ENTITY_ID: ENTITY_HYGROSTAT},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_HYGROSTAT)
    assert state.attributes.get(ATTR_MODE) == "eco"


async def test_turn_on(menuai: menuai) -> None:
    """Test turn on device."""
    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ACTION) == "off"

    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ACTION) == "drying"


async def test_turn_off(menuai: menuai) -> None:
    """Test turn off device."""
    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ACTION) == "drying"

    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ACTION) == "off"


async def test_toggle(menuai: menuai) -> None:
    """Test toggle device."""
    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        HUMIDITY_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: ENTITY_DEHUMIDIFIER},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DEHUMIDIFIER)
    assert state.state == STATE_ON
