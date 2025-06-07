"""The tests for the demo button component."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.kitchen_sink import DOMAIN
from menuai.components.notify import (
    ATTR_MESSAGE,
    DOMAIN as NOTIFY_DOMAIN,
    SERVICE_SEND_MESSAGE,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

ENTITY_DIRECT_MESSAGE = "notify.mybox_personal_notifier"


@pytest.fixture
async def notify_only() -> AsyncGenerator[None]:
    """Enable only the button platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.NOTIFY],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, notify_only: None):
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_DIRECT_MESSAGE)
    assert state
    assert state.state == STATE_UNKNOWN


async def test_send_message(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test pressing the button."""
    state = menuai.states.get(ENTITY_DIRECT_MESSAGE)
    assert state
    assert state.state == STATE_UNKNOWN

    now = dt_util.parse_datetime("2021-01-09 12:00:00+00:00")
    freezer.move_to(now)
    await menuai.services.async_call(
        NOTIFY_DOMAIN,
        SERVICE_SEND_MESSAGE,
        {ATTR_ENTITY_ID: ENTITY_DIRECT_MESSAGE, ATTR_MESSAGE: "You have an update!"},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_DIRECT_MESSAGE)
    assert state
    assert state.state == now.isoformat()
