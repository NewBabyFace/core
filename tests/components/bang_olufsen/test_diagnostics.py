"""Test bang_olufsen config entry diagnostics."""

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.core import menuai
from menuai.helpers.entity_registry import EntityRegistry

from .const import TEST_BUTTON_EVENT_ENTITY_ID

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_async_get_config_entry_diagnostics(
    menuai: menuai,
    entity_registry: EntityRegistry,
    menuai_client: ClientSessionGenerator,
    integration: None,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""

    # Enable an Event entity
    entity_registry.async_update_entity(TEST_BUTTON_EVENT_ENTITY_ID, disabled_by=None)
    menuai.config_entries.async_schedule_reload(mock_config_entry.entry_id)

    result = await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    )

    assert result == snapshot(
        exclude=props(
            "created_at",
            "entry_id",
            "id",
            "last_changed",
            "last_reported",
            "last_updated",
            "media_position_updated_at",
            "modified_at",
        )
    )
