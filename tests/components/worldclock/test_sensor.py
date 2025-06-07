"""The test for the World clock sensor platform."""

from datetime import tzinfo

import pytest

from menuai.components.worldclock.const import CONF_TIME_FORMAT, DEFAULT_NAME
from menuai.const import CONF_NAME, CONF_TIME_ZONE
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry


@pytest.fixture
async def time_zone() -> tzinfo | None:
    """Fixture for time zone."""
    return await dt_util.async_get_time_zone("America/New_York")


async def test_time_from_config_entry(
    menuai: menuai, time_zone: tzinfo | None, loaded_entry: MockConfigEntry
) -> None:
    """Test the time at a different location."""

    state = menuai.states.get("sensor.worldclock_sensor")
    assert state is not None

    assert state.state == dt_util.now(time_zone=time_zone).strftime("%H:%M")


@pytest.mark.parametrize(
    "get_config",
    [
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_TIME_ZONE: "America/New_York",
            CONF_TIME_FORMAT: "%a, %b %d, %Y %I:%M %p",
        }
    ],
)
async def test_time_format(
    menuai: menuai, time_zone: tzinfo | None, loaded_entry: MockConfigEntry
) -> None:
    """Test time_format setting."""

    state = menuai.states.get("sensor.worldclock_sensor")
    assert state is not None

    assert state.state == dt_util.now(time_zone=time_zone).strftime(
        "%a, %b %d, %Y %I:%M %p"
    )
