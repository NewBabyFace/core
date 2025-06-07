"""Tests for the Teslemetry integration."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.teslemetry.const import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import CONFIG

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai, platforms: list[Platform] | None = None
) -> MockConfigEntry:
    """Set up the Teslemetry platform."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN, data=CONFIG, minor_version=2, unique_id="abc-123"
    )
    mock_entry.add_to_menuai(menuai)

    if platforms is None:
        await menuai.config_entries.async_setup(mock_entry.entry_id)
    else:
        with patch("menuai.components.teslemetry.PLATFORMS", platforms):
            await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    return mock_entry


async def reload_platform(
    menuai: menuai, entry: MockConfigEntry, platforms: list[Platform] | None = None
):
    """Reload the Teslemetry platform."""

    if platforms is None:
        await menuai.config_entries.async_reload(entry.entry_id)
    else:
        with patch("menuai.components.teslemetry.PLATFORMS", platforms):
            await menuai.config_entries.async_reload(entry.entry_id)
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
