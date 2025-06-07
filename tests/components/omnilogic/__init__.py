"""Tests for the Omnilogic integration."""

from unittest.mock import patch

from menuai.components.omnilogic.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from .const import TELEMETRY

from tests.common import MockConfigEntry


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Mock integration setup."""
    with (
        patch(
            "menuai.components.omnilogic.OmniLogic.connect",
            return_value=True,
        ),
        patch(
            "menuai.components.omnilogic.OmniLogic.get_telemetry_data",
            return_value={},
        ),
        patch(
            "menuai.components.omnilogic.coordinator.OmniLogicUpdateCoordinator._async_update_data",
            return_value=TELEMETRY,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
            entry_id="6fa019921cf8e7a3f57a3c2ed001a10d",
        )
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        return entry
