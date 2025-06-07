"""Test util for the homekit integration."""

from unittest.mock import patch

from menuai.components.homekit.const import DOMAIN
from menuai.const import CONF_NAME, CONF_PORT
from menuai.core import menuai

from tests.common import MockConfigEntry

PATH_HOMEKIT = "menuai.components.homekit"


async def async_init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the homekit integration in MenuAI."""

    with patch(f"{PATH_HOMEKIT}.HomeKit.async_start"):
        entry = MockConfigEntry(
            domain=DOMAIN, data={CONF_NAME: "mock_name", CONF_PORT: 12345}
        )
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        return entry


async def async_init_entry(menuai: menuai, entry: MockConfigEntry):
    """Set up the homekit integration in MenuAI."""

    with patch(f"{PATH_HOMEKIT}.HomeKit.async_start"):
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        return entry
