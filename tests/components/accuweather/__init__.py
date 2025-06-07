"""Tests for AccuWeather."""

from menuai.components.accuweather.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the AccuWeather integration in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data={
            "api_key": "32-character-string-1234567890qw",
            "latitude": 55.55,
            "longitude": 122.12,
            "name": "Home",
        },
    )

    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
