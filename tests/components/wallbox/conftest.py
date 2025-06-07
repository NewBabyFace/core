"""Test fixtures for the Wallbox integration."""

import pytest

from menuai.components.wallbox.const import CONF_STATION, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def entry(menuai: menuai) -> MockConfigEntry:
    """Return mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test_username",
            CONF_PASSWORD: "test_password",
            CONF_STATION: "12345",
        },
        entry_id="testEntry",
    )
    entry.add_to_menuai(menuai)
    return entry
