"""Define test fixtures for IPMA."""

from unittest.mock import patch

import pytest

from menuai.components.ipma.const import DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai

from . import MockLocation

from tests.common import MockConfigEntry


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Define a config entry fixture."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Home",
            CONF_LATITUDE: 0,
            CONF_LONGITUDE: 0,
        },
    )
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
async def init_integration(
    menuai: menuai, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the IPMA integration for testing."""
    config_entry.add_to_menuai(menuai)

    with patch("pyipma.location.Location.get", return_value=MockLocation()):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        return config_entry
