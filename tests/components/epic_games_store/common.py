"""Common methods used across tests for Epic Games Store."""

from unittest.mock import patch

from menuai.components.epic_games_store.const import DOMAIN
from menuai.const import CONF_COUNTRY, CONF_LANGUAGE
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import MOCK_COUNTRY, MOCK_LANGUAGE

from tests.common import MockConfigEntry


async def setup_platform(menuai: menuai, platform: str) -> MockConfigEntry:
    """Set up the Epic Games Store platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LANGUAGE: MOCK_LANGUAGE,
            CONF_COUNTRY: MOCK_COUNTRY,
        },
        unique_id=f"freegames-{MOCK_LANGUAGE}-{MOCK_COUNTRY}",
    )
    mock_entry.add_to_menuai(menuai)

    with patch("menuai.components.epic_games_store.PLATFORMS", [platform]):
        assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    return mock_entry
