"""The tests for the WSDOT platform."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from menuai.components.wsdot.sensor import (
    CONF_API_KEY,
    CONF_ID,
    CONF_NAME,
    CONF_TRAVEL_TIMES,
    DOMAIN,
)
from menuai.const import CONF_PLATFORM
from menuai.core import menuai
from menuai.setup import async_setup_component

config = {
    CONF_API_KEY: "foo",
    CONF_TRAVEL_TIMES: [{CONF_ID: 96, CONF_NAME: "I90 EB"}],
}


async def test_setup_with_config(
    menuai: menuai, mock_travel_time: AsyncMock
) -> None:
    """Test the platform setup with configuration."""
    assert await async_setup_component(
        menuai, "sensor", {"sensor": [{CONF_PLATFORM: DOMAIN, **config}]}
    )

    state = menuai.states.get("sensor.i90_eb")
    assert state is not None
    assert state.name == "I90 EB"
    assert state.state == "11"
    assert (
        state.attributes["Description"]
        == "Downtown Seattle to Downtown Bellevue via I-90"
    )
    assert state.attributes["TimeUpdated"] == datetime(
        2017, 1, 21, 15, 10, tzinfo=timezone(timedelta(hours=-8))
    )
