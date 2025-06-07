"""Tests for the SwitchBot Cloud integration."""

from menuai.components.switchbot_cloud.const import DOMAIN
from menuai.const import CONF_API_KEY, CONF_API_TOKEN
from menuai.core import menuai

from tests.common import MockConfigEntry


async def configure_integration(menuai: menuai) -> MockConfigEntry:
    """Configure the integration."""
    config = {
        CONF_API_TOKEN: "test-token",
        CONF_API_KEY: "test-api-key",
    }
    entry = MockConfigEntry(
        domain=DOMAIN, data=config, entry_id="123456", unique_id="123456"
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
