"""Define tests for the Acmeda config flow."""

import pytest

from menuai.components.acmeda.const import DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_hub_run")
async def test_sensor_id_migration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test migrating unique id."""
    mock_config_entry.add_to_menuai(menuai)
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN, DOMAIN, 1234567890123, config_entry=mock_config_entry
    )
    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    entities = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    assert len(entities) == 1
    assert entities[0].unique_id == "1234567890123"
