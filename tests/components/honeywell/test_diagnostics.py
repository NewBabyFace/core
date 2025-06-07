"""Test Honeywell diagnostics."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

YAML_CONFIG = {"username": "test-user", "password": "test-password"}


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    location: MagicMock,
    another_device: MagicMock,
) -> None:
    """Test config entry diagnostics for Honeywell."""

    location.devices_by_id[another_device.deviceid] = another_device
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert menuai.states.async_entity_ids_count() == 8

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

    assert result == snapshot
