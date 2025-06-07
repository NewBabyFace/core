"""Tests for the Tesla Fleet integration."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.tesla_fleet.const import CLIENT_ID, DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai,
    config_entry: MockConfigEntry,
    platforms: list[Platform] | None = None,
) -> None:
    """Set up the Tesla Fleet platform."""

    assert await async_setup_component(menuai, "application_credentials", {})
    await async_import_client_credential(
        menuai,
        DOMAIN,
        ClientCredential(CLIENT_ID, "", "MenuAI"),
        DOMAIN,
    )

    config_entry.add_to_menuai(menuai)

    if platforms is None:
        await menuai.config_entries.async_setup(config_entry.entry_id)
    else:
        with patch("menuai.components.tesla_fleet.PLATFORMS", platforms):
            await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


def assert_entities(
    menuai: menuai,
    entry_id: str,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that all entities match their snapshot."""

    entity_entries = er.async_entries_for_config_entry(entity_registry, entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert (state := menuai.states.get(entity_entry.entity_id))
        assert state == snapshot(name=f"{entity_entry.entity_id}-state")


def assert_entities_alt(
    menuai: menuai,
    entry_id: str,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that all entities match their alt snapshot."""
    entity_entries = er.async_entries_for_config_entry(entity_registry, entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert (state := menuai.states.get(entity_entry.entity_id))
        assert state == snapshot(name=f"{entity_entry.entity_id}-statealt")
