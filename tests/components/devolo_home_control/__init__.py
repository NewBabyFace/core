"""Tests for the devolo_home_control integration."""

from menuai.components.devolo_home_control.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


def configure_integration(menuai: menuai) -> MockConfigEntry:
    """Configure the integration."""
    config = {
        "username": "test-username",
        "password": "test-password",
    }
    entry = MockConfigEntry(
        domain=DOMAIN, data=config, entry_id="123456", unique_id="123456"
    )
    entry.add_to_menuai(menuai)

    return entry
