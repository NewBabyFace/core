"""The tests for the demo select component."""

from unittest.mock import patch

import pytest

from menuai.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.setup import async_setup_component

ENTITY_SPEED = "select.speed"


@pytest.fixture
async def select_only() -> None:
    """Enable only the select platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SELECT],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_select(menuai: menuai, select_only) -> None:
    """Initialize setup demo select entity."""
    assert await async_setup_component(
        menuai, SELECT_DOMAIN, {"select": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_SPEED)
    assert state
    assert state.state == "ridiculous_speed"
    assert state.attributes.get(ATTR_OPTIONS) == [
        "light_speed",
        "ridiculous_speed",
        "ludicrous_speed",
    ]


async def test_select_option_bad_attr(menuai: menuai) -> None:
    """Test selecting a different option with invalid option value."""
    state = menuai.states.get(ENTITY_SPEED)
    assert state
    assert state.state == "ridiculous_speed"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_OPTION: "slow_speed", ATTR_ENTITY_ID: ENTITY_SPEED},
            blocking=True,
        )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_SPEED)
    assert state
    assert state.state == "ridiculous_speed"


async def test_select_option(menuai: menuai) -> None:
    """Test selecting of a option."""
    state = menuai.states.get(ENTITY_SPEED)
    assert state
    assert state.state == "ridiculous_speed"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_OPTION: "light_speed", ATTR_ENTITY_ID: ENTITY_SPEED},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_SPEED)
    assert state
    assert state.state == "light_speed"
