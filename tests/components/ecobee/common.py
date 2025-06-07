"""Common methods used across tests for Ecobee."""

from unittest.mock import patch

from menuai.components.ecobee.const import CONF_REFRESH_TOKEN, DOMAIN
from menuai.const import CONF_API_KEY
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai,
    platforms: str | list[str],
) -> MockConfigEntry:
    """Set up the ecobee platform."""
    mock_entry = MockConfigEntry(
        title=DOMAIN,
        domain=DOMAIN,
        data={
            CONF_API_KEY: "ABC123",
            CONF_REFRESH_TOKEN: "EFG456",
        },
    )
    mock_entry.add_to_menuai(menuai)

    platforms = [platforms] if isinstance(platforms, str) else platforms

    with patch("menuai.components.ecobee.PLATFORMS", platforms):
        await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()
    return mock_entry
