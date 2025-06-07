"""Tests for Met.no."""

from unittest.mock import patch

from menuai.components.met.const import CONF_TRACK_HOME, DOMAIN
from menuai.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, track_home: bool = False
) -> MockConfigEntry:
    """Set up the Met integration in MenuAI."""
    entry_data = {
        CONF_NAME: "test",
        CONF_LATITUDE: 0,
        CONF_LONGITUDE: 1.0,
        CONF_ELEVATION: 1.0,
    }

    if track_home:
        entry_data = {CONF_TRACK_HOME: True}

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    with patch(
        "menuai.components.met.coordinator.metno.MetWeatherData.fetching_data",
        return_value=True,
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
