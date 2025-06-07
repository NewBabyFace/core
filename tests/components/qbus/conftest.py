"""Test fixtures for qbus."""

import json

import pytest

from menuai.components.qbus.const import CONF_SERIAL_NUMBER, DOMAIN
from menuai.const import CONF_ID
from menuai.core import menuai
from menuai.util.json import JsonObjectType

from .const import FIXTURE_PAYLOAD_CONFIG, TOPIC_CONFIG

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    load_json_object_fixture,
)


@pytest.fixture
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Return the default mocked config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="000001",
        data={
            CONF_ID: "UL1",
            CONF_SERIAL_NUMBER: "000001",
        },
    )
    config_entry.add_to_menuai(menuai)
    return config_entry


@pytest.fixture
def payload_config() -> JsonObjectType:
    """Return the config topic payload."""
    return load_json_object_fixture(FIXTURE_PAYLOAD_CONFIG, DOMAIN)


@pytest.fixture
async def setup_integration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    payload_config: JsonObjectType,
) -> None:
    """Set up the integration."""

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, TOPIC_CONFIG, json.dumps(payload_config))
    await menuai.async_block_till_done()
