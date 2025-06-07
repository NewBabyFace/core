"""The tests for the demo datetime component."""

from unittest.mock import patch

import pytest

from menuai.components.datetime import (
    ATTR_DATETIME,
    DOMAIN as DATETIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_DATETIME = "datetime.date_and_time"


@pytest.fixture
async def datetime_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.DATETIME],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_datetime(menuai: menuai, datetime_only) -> None:
    """Initialize setup demo datetime."""
    assert await async_setup_component(
        menuai, DATETIME_DOMAIN, {"datetime": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_DATETIME)
    assert state.state == "2020-01-01T12:00:00+00:00"


async def test_set_datetime(menuai: menuai) -> None:
    """Test set datetime service."""
    await menuai.config.async_set_time_zone("UTC")
    await menuai.services.async_call(
        DATETIME_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_DATETIME, ATTR_DATETIME: "2021-02-03 01:02:03"},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DATETIME)
    assert state.state == "2021-02-03T01:02:03+00:00"
