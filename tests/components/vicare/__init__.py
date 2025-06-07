"""Test for ViCare."""

from __future__ import annotations

from typing import Final

from menuai.components.vicare.const import CONF_HEATING_TYPE
from menuai.const import CONF_CLIENT_ID, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry

MODULE = "menuai.components.vicare"

ENTRY_CONFIG: Final[dict[str, str]] = {
    CONF_USERNAME: "foo@bar.com",
    CONF_PASSWORD: "1234",
    CONF_CLIENT_ID: "5678",
    CONF_HEATING_TYPE: "auto",
}

MOCK_MAC = "B874241B7B9"


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
