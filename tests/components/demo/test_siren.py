"""The tests for the demo siren component."""

from unittest.mock import call, patch

import pytest

from menuai.components.siren import (
    ATTR_AVAILABLE_TONES,
    ATTR_TONE,
    ATTR_VOLUME_LEVEL,
    DOMAIN as SIREN_DOMAIN,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_SIREN = "siren.siren"
ENTITY_SIREN_WITH_ALL_FEATURES = "siren.siren_with_all_features"


@pytest.fixture
async def siren_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SIREN],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_siren(menuai: menuai, siren_only: None):
    """Initialize setup demo siren."""
    assert await async_setup_component(
        menuai, SIREN_DOMAIN, {"siren": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_ON
    assert ATTR_AVAILABLE_TONES not in state.attributes


def test_all_setup_params(menuai: menuai) -> None:
    """Test the setup with all parameters."""
    state = menuai.states.get(ENTITY_SIREN_WITH_ALL_FEATURES)
    assert state.attributes.get(ATTR_AVAILABLE_TONES) == ["fire", "alarm"]


async def test_turn_on(menuai: menuai) -> None:
    """Test turn on device."""
    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_ON

    # Test that an invalid tone will raise a ValueError
    with pytest.raises(ValueError):
        await menuai.services.async_call(
            SIREN_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ENTITY_SIREN_WITH_ALL_FEATURES, ATTR_TONE: "invalid_tone"},
            blocking=True,
        )


async def test_turn_off(menuai: menuai) -> None:
    """Test turn off device."""
    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_OFF


async def test_toggle(menuai: menuai) -> None:
    """Test toggle device."""
    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SIREN_DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_SIREN}, blocking=True
    )
    state = menuai.states.get(ENTITY_SIREN)
    assert state.state == STATE_ON


async def test_turn_on_strip_attributes(menuai: menuai) -> None:
    """Test attributes are stripped from turn_on service call when not supported."""
    with patch(
        "menuai.components.demo.siren.DemoSiren.async_turn_on"
    ) as svc_call:
        await menuai.services.async_call(
            SIREN_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ENTITY_SIREN, ATTR_VOLUME_LEVEL: 1},
            blocking=True,
        )
        assert svc_call.called
        assert svc_call.call_args_list[0] == call()
