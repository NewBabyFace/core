"""The tests for the demo time component."""

from unittest.mock import patch

import pytest

from menuai.components.time import (
    ATTR_TIME,
    DOMAIN as TIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_TIME = "time.time"


@pytest.fixture
async def time_only() -> None:
    """Enable only the time platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.TIME],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_datetime(menuai: menuai, time_only) -> None:
    """Initialize setup demo time."""
    assert await async_setup_component(
        menuai, TIME_DOMAIN, {"time": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_TIME)
    assert state.state == "12:00:00"


async def test_set_value(menuai: menuai) -> None:
    """Test set value service."""
    await menuai.services.async_call(
        TIME_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_TIME, ATTR_TIME: "01:02:03"},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_TIME)
    assert state.state == "01:02:03"
