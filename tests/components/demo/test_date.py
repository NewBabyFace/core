"""The tests for the demo date component."""

from unittest.mock import patch

import pytest

from menuai.components.date import (
    ATTR_DATE,
    DOMAIN as DATE_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_DATE = "date.date"


@pytest.fixture
async def date_only() -> None:
    """Enable only the date platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.DATE],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_date(menuai: menuai, date_only) -> None:
    """Initialize setup demo date."""
    assert await async_setup_component(
        menuai, DATE_DOMAIN, {"date": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_DATE)
    assert state.state == "2020-01-01"


async def test_set_datetime(menuai: menuai) -> None:
    """Test set datetime service."""
    await menuai.services.async_call(
        DATE_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_DATE, ATTR_DATE: "2021-02-03"},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_DATE)
    assert state.state == "2021-02-03"
