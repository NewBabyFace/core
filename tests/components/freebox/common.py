"""Common methods used across tests for Freebox."""

from unittest.mock import patch

from menuai.components.freebox.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import MOCK_HOST, MOCK_PORT

from tests.common import MockConfigEntry


async def setup_platform(menuai: menuai, platform: str) -> MockConfigEntry:
    """Set up the Freebox platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        unique_id=MOCK_HOST,
    )
    mock_entry.add_to_menuai(menuai)

    with patch("menuai.components.freebox.PLATFORMS", [platform]):
        assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    return mock_entry
