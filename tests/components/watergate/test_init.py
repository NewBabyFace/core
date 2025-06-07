"""Tests for the Watergate integration init module."""

from collections.abc import Generator
from unittest.mock import patch

from menuai.components.valve import ValveState
from menuai.components.watergate.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_integration
from .const import MOCK_WEBHOOK_ID

from tests.common import ANY, AsyncMock, MockConfigEntry
from tests.typing import ClientSessionGenerator


async def test_async_setup_entry(
    menuai: menuai,
    mock_entry: MockConfigEntry,
    mock_watergate_client: Generator[AsyncMock],
) -> None:
    """Test setting up the Watergate integration."""
    menuai.config.internal_url = "http://menuaiio.local"

    with (
        patch("menuai.components.watergate.async_register") as mock_webhook,
    ):
        await init_integration(menuai, mock_entry)

        assert mock_entry.state is ConfigEntryState.LOADED

        mock_webhook.assert_called_once_with(
            menuai,
            DOMAIN,
            "Watergate",
            MOCK_WEBHOOK_ID,
            ANY,
        )
        mock_watergate_client.async_set_webhook_url.assert_called_once_with(
            f"http://menuaiio.local/api/webhook/{MOCK_WEBHOOK_ID}"
        )
        mock_watergate_client.async_get_device_state.assert_called_once()


async def test_handle_webhook(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    mock_entry: MockConfigEntry,
    mock_watergate_client: Generator[AsyncMock],
) -> None:
    """Test handling webhook events."""
    await init_integration(menuai, mock_entry)

    entity_id = "valve.sonic"

    registered_entity = menuai.states.get(entity_id)
    assert registered_entity
    assert registered_entity.state == ValveState.OPEN

    valve_change_data = {
        "type": "valve",
        "data": {"state": "closed"},
    }
    client = await menuai_client_no_auth()
    await client.post(f"/api/webhook/{MOCK_WEBHOOK_ID}", json=valve_change_data)

    await menuai.async_block_till_done()  # Ensure the webhook is processed

    assert menuai.states.get(entity_id).state == ValveState.CLOSED

    valve_change_data = {
        "type": "valve",
        "data": {"state": "open"},
    }

    await client.post(f"/api/webhook/{MOCK_WEBHOOK_ID}", json=valve_change_data)

    await menuai.async_block_till_done()  # Ensure the webhook is processed

    assert menuai.states.get(entity_id).state == ValveState.OPEN
