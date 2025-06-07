"""The tests for the Switch component."""

import pytest

from menuai import core
from menuai.components import switch
from menuai.const import CONF_PLATFORM
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import common
from .common import MockSwitch

from tests.common import MockUser, setup_test_component_platform


@pytest.fixture(autouse=True)
def entities(
    menuai: menuai, mock_switch_entities: list[MockSwitch]
) -> list[MockSwitch]:
    """Initialize the test switch."""
    setup_test_component_platform(menuai, switch.DOMAIN, mock_switch_entities)
    return mock_switch_entities


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_methods(menuai: menuai, entities: list[MockSwitch]) -> None:
    """Test is_on, turn_on, turn_off methods."""
    switch_1, switch_2, switch_3 = entities
    assert await async_setup_component(
        menuai, switch.DOMAIN, {switch.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await menuai.async_block_till_done()
    assert switch.is_on(menuai, switch_1.entity_id)
    assert not switch.is_on(menuai, switch_2.entity_id)
    assert not switch.is_on(menuai, switch_3.entity_id)

    await common.async_turn_off(menuai, switch_1.entity_id)
    await common.async_turn_on(menuai, switch_2.entity_id)

    assert not switch.is_on(menuai, switch_1.entity_id)
    assert switch.is_on(menuai, switch_2.entity_id)

    # Turn all off
    await common.async_turn_off(menuai)

    assert not switch.is_on(menuai, switch_1.entity_id)
    assert not switch.is_on(menuai, switch_2.entity_id)
    assert not switch.is_on(menuai, switch_3.entity_id)

    # Turn all on
    await common.async_turn_on(menuai)

    assert switch.is_on(menuai, switch_1.entity_id)
    assert switch.is_on(menuai, switch_2.entity_id)
    assert switch.is_on(menuai, switch_3.entity_id)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_switch_context(
    menuai: menuai,
    entities,
    menuai_admin_user: MockUser,
) -> None:
    """Test that switch context works."""
    assert await async_setup_component(menuai, "switch", {"switch": {"platform": "test"}})

    await menuai.async_block_till_done()

    state = menuai.states.get("switch.ac")
    assert state is not None

    await menuai.services.async_call(
        "switch",
        "toggle",
        {"entity_id": state.entity_id},
        True,
        core.Context(user_id=menuai_admin_user.id),
    )

    state2 = menuai.states.get("switch.ac")
    assert state2 is not None
    assert state.state != state2.state
    assert state2.context.user_id == menuai_admin_user.id
