"""Test init."""

from unittest.mock import AsyncMock

from menuai.components.light import DOMAIN as LIGHT_DOMAIN
from menuai.components.niko_home_control.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_migrate_entry(
    menuai: menuai, entity_registry: er.EntityRegistry, mock_setup_entry: AsyncMock
) -> None:
    """Validate that the unique_id is migrated to the new unique_id."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        minor_version=1,
        data={CONF_HOST: "192.168.0.123"},
    )
    config_entry.add_to_menuai(menuai)
    entity_entry = entity_registry.async_get_or_create(
        LIGHT_DOMAIN, DOMAIN, "light-1", config_entry=config_entry
    )
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    entity_entry = entity_registry.async_get(entity_entry.entity_id)

    assert config_entry.minor_version == 2
    assert (
        entity_registry.async_get(entity_entry.entity_id).unique_id
        == f"{config_entry.entry_id}-1"
    )
