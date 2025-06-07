"""The tests for the demo switch component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.demo import DOMAIN
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

SWITCH_ENTITY_IDS = ["switch.decorative_lights", "switch.ac"]


@pytest.fixture
def switch_only() -> Generator[None]:
    """Enable only the switch platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, switch_only: None) -> None:
    """Set up demo component."""
    assert await async_setup_component(
        menuai, SWITCH_DOMAIN, {SWITCH_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()


@pytest.mark.parametrize("switch_entity_id", SWITCH_ENTITY_IDS)
async def test_turn_on(menuai: menuai, switch_entity_id: str) -> None:
    """Test switch turn on method."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_ON


@pytest.mark.parametrize("switch_entity_id", SWITCH_ENTITY_IDS)
async def test_turn_off(menuai: menuai, switch_entity_id: str) -> None:
    """Test switch turn off method."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("switch_entity_id", SWITCH_ENTITY_IDS)
async def test_turn_off_without_entity_id(
    menuai: menuai, switch_entity_id: str
) -> None:
    """Test switch turn off all switches."""
    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: "all"}, blocking=True
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: "all"}, blocking=True
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_OFF
