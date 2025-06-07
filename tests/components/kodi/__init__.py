"""Tests for the Kodi integration."""

from unittest.mock import patch

from menuai.components.kodi.const import CONF_WS_PORT, DOMAIN
from menuai.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from menuai.core import menuai

from .util import MockConnection

from tests.common import MockConfigEntry


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the Kodi integration in MenuAI."""
    entry_data = {
        CONF_NAME: "name",
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 8080,
        CONF_WS_PORT: 9090,
        CONF_USERNAME: "user",
        CONF_PASSWORD: "pass",
        CONF_SSL: False,
    }
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data, title="name")
    entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.kodi.Kodi.ping", return_value=True),
        patch(
            "menuai.components.kodi.Kodi.get_application_properties",
            return_value={"version": {"major": 1, "minor": 1}},
        ),
        patch(
            "menuai.components.kodi.get_kodi_connection",
            return_value=MockConnection(),
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
