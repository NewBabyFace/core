"""Test fixtures for Tasmota component."""

from unittest.mock import patch

from hatasmota.discovery import get_status_sensor_entities
import pytest

from menuai.components.tasmota.const import (
    CONF_DISCOVERY_PREFIX,
    DEFAULT_PREFIX,
    DOMAIN,
)
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.light.conftest import mock_light_profiles  # noqa: F401


@pytest.fixture(autouse=True)
def disable_debounce():
    """Set MQTT debounce timer to zero."""
    with patch("hatasmota.mqtt.DEBOUNCE_TIMEOUT", 0):
        yield


@pytest.fixture
def status_sensor_disabled():
    """Fixture to allow overriding MQTT config."""
    return True


@pytest.fixture(autouse=True)
def disable_status_sensor(status_sensor_disabled):
    """Disable Tasmota status sensor."""
    wraps = None if status_sensor_disabled else get_status_sensor_entities
    with patch("hatasmota.discovery.get_status_sensor_entities", wraps=wraps):
        yield


async def setup_tasmota_helper(menuai: menuai) -> None:
    """Set up Tasmota."""
    menuai.config.components.add("tasmota")

    entry = MockConfigEntry(
        data={CONF_DISCOVERY_PREFIX: DEFAULT_PREFIX},
        domain=DOMAIN,
        title="Tasmota",
    )

    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert "tasmota" in menuai.config.components


@pytest.fixture
async def setup_tasmota(menuai: menuai) -> None:
    """Set up Tasmota."""
    await setup_tasmota_helper(menuai)
