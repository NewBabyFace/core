"""Common methods used across tests for Abode."""

from unittest.mock import patch

from menuai.components.abode import DOMAIN
from menuai.components.abode.const import CONF_POLLING
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def setup_platform(menuai: menuai, platform: str) -> MockConfigEntry:
    """Set up the Abode platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "user@email.com",
            CONF_PASSWORD: "password",
            CONF_POLLING: False,
        },
    )
    mock_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.abode.PLATFORMS", [platform]),
        patch("jaraco.abode.event_controller.sio"),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    return mock_entry
