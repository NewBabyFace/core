"""Tests for the Onkyo integration."""

from unittest.mock import AsyncMock, Mock, patch

from menuai.components.onkyo.receiver import Receiver, ReceiverInfo
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry


def create_receiver_info(id: int) -> ReceiverInfo:
    """Create an empty receiver info object for testing."""
    return ReceiverInfo(
        host=f"host {id}",
        port=id,
        model_name=f"type {id}",
        identifier=f"id{id}",
    )


def create_connection(id: int) -> Mock:
    """Create an mock connection object for testing."""
    connection = Mock()
    connection.host = f"host {id}"
    connection.port = 0
    connection.name = f"type {id}"
    connection.identifier = f"id{id}"
    return connection


def create_config_entry_from_info(info: ReceiverInfo) -> MockConfigEntry:
    """Create a config entry from receiver info."""
    data = {CONF_HOST: info.host}
    options = {
        "volume_resolution": 80,
        "max_volume": 100,
        "input_sources": {"12": "tv"},
        "listening_modes": {"00": "stereo"},
    }

    return MockConfigEntry(
        data=data,
        options=options,
        title=info.model_name,
        domain="onkyo",
        unique_id=info.identifier,
    )


def create_empty_config_entry() -> MockConfigEntry:
    """Create an empty config entry for use in unit tests."""
    data = {CONF_HOST: ""}
    options = {
        "volume_resolution": 80,
        "max_volume": 100,
        "input_sources": {"12": "tv"},
        "listening_modes": {"00": "stereo"},
    }

    return MockConfigEntry(
        data=data,
        options=options,
        title="Unit test Onkyo",
        domain="onkyo",
        unique_id="onkyo_unique_id",
    )


async def setup_integration(
    menuai: menuai, config_entry: MockConfigEntry, receiver_info: ReceiverInfo
) -> None:
    """Fixture for setting up the component."""

    config_entry.add_to_menuai(menuai)

    mock_receiver = AsyncMock()
    mock_receiver.conn.close = Mock()
    mock_receiver.callbacks.connect = Mock()
    mock_receiver.callbacks.update = Mock()

    with (
        patch(
            "menuai.components.onkyo.async_interview",
            return_value=receiver_info,
        ),
        patch.object(Receiver, "async_create", return_value=mock_receiver),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
