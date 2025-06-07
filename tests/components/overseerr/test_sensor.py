"""Tests for the Overseerr sensor platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.overseerr import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import call_webhook, setup_integration

from tests.common import (
    MockConfigEntry,
    async_load_json_object_fixture,
    snapshot_platform,
)
from tests.typing import ClientSessionGenerator


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.overseerr.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_webhook_trigger_update(
    menuai: menuai,
    mock_overseerr_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test all entities."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("sensor.overseerr_available_requests").state == "8"

    mock_overseerr_client.get_request_count.return_value.available = 7
    client = await menuai_client_no_auth()

    await call_webhook(
        menuai,
        await async_load_json_object_fixture(
            menuai, "webhook_request_automatically_approved.json", DOMAIN
        ),
        client,
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.overseerr_available_requests").state == "7"
