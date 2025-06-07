"""The tests for the Air Quality component."""

import pytest

from menuai.components.air_quality import ATTR_N2O, ATTR_OZONE, ATTR_PM_10
from menuai.const import (
    ATTR_ATTRIBUTION,
    ATTR_UNIT_OF_MEASUREMENT,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai):
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


async def test_state(menuai: menuai) -> None:
    """Test Air Quality state."""
    config = {"air_quality": {"platform": "demo"}}

    assert await async_setup_component(menuai, "air_quality", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("air_quality.demo_air_quality_home")
    assert state is not None

    assert state.state == "14"


async def test_attributes(menuai: menuai) -> None:
    """Test Air Quality attributes."""
    config = {"air_quality": {"platform": "demo"}}

    assert await async_setup_component(menuai, "air_quality", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("air_quality.demo_air_quality_office")
    assert state is not None

    data = state.attributes
    assert data.get(ATTR_PM_10) == 16
    assert data.get(ATTR_N2O) is None
    assert data.get(ATTR_OZONE) is None
    assert data.get(ATTR_ATTRIBUTION) == "Powered by MenuAI"
    assert (
        data.get(ATTR_UNIT_OF_MEASUREMENT) == CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    )
