"""Test init of Ohme integration."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.ohme.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test loading and unloading the integration."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device(
    mock_client: MagicMock,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Snapshot the device from registry."""
    await setup_integration(menuai, mock_config_entry)

    device = device_registry.async_get_device({(DOMAIN, mock_client.serial)})
    assert device
    assert device == snapshot
