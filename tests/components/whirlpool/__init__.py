"""Tests for the Whirlpool Sixth Sense integration."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.whirlpool.const import CONF_BRAND, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.helpers.entity_registry import EntityRegistry

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, region: str = "EU", brand: str = "Whirlpool"
) -> MockConfigEntry:
    """Set up the Whirlpool integration in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "nobody",
            CONF_PASSWORD: "qwerty",
            CONF_REGION: region,
            CONF_BRAND: brand,
        },
    )

    return await init_integration_with_entry(menuai, entry)


async def init_integration_with_entry(
    menuai: menuai, entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the Whirlpool integration in MenuAI."""
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    return entry


def snapshot_whirlpool_entities(
    menuai: menuai,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
    platform: Platform,
) -> None:
    """Snapshot Whirlpool entities."""
    entities = menuai.states.async_all(platform)
    for entity_state in entities:
        entity_entry = entity_registry.async_get(entity_state.entity_id)
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert entity_state == snapshot(name=f"{entity_entry.entity_id}-state")


async def trigger_attr_callback(
    menuai: menuai, mock_api_instance: MagicMock
) -> None:
    """Simulate an update trigger from the API."""

    for call in mock_api_instance.register_attr_callback.call_args_list:
        update_ha_state_cb = call[0][0]
        update_ha_state_cb()
    await menuai.async_block_till_done()
