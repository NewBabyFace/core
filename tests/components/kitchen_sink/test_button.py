"""The tests for the demo button component."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.kitchen_sink import DOMAIN
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

ENTITY_RESTART = "button.power_strip_with_2_sockets_restart"


@pytest.fixture
async def button_only() -> None:
    """Enable only the button platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.BUTTON],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, button_only):
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_RESTART)
    assert state
    assert state.state == STATE_UNKNOWN


async def test_press(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Test pressing the button."""
    state = menuai.states.get(ENTITY_RESTART)
    assert state
    assert state.state == STATE_UNKNOWN

    now = dt_util.parse_datetime("2021-01-09 12:00:00+00:00")
    freezer.move_to(now)
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: ENTITY_RESTART},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_RESTART)
    assert state
    assert state.state == now.isoformat()
