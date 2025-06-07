"""Test init."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_setup_entry(
    menuai: menuai,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test migration of config entry from v1."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    assert (
        dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
        == snapshot
    )

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
