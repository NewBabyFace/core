"""Tests for the Ituran integration."""

from unittest.mock import AsyncMock

from pyituran.exceptions import IturanApiError, IturanAuthError
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_ituran: AsyncMock,
) -> None:
    """Test the Ituran configuration entry loading/unloading."""
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_ituran: AsyncMock,
    snapshot: SnapshotAssertion,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the device information."""
    await setup_integration(menuai, mock_config_entry)

    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    assert device_entries == snapshot


async def test_remove_stale_devices(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_ituran: AsyncMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test that devices not returned by the service are removed."""
    await setup_integration(menuai, mock_config_entry)
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 1

    mock_ituran.get_vehicles.return_value = []
    await mock_config_entry.runtime_data.async_refresh()
    await menuai.async_block_till_done()
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 0


async def test_recover_from_errors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_ituran: AsyncMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Verify we can recover from service Errors."""

    await setup_integration(menuai, mock_config_entry)
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 1

    mock_ituran.get_vehicles.side_effect = IturanApiError
    await mock_config_entry.runtime_data.async_refresh()
    await menuai.async_block_till_done()
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 1

    mock_ituran.get_vehicles.side_effect = IturanAuthError
    await mock_config_entry.runtime_data.async_refresh()
    await menuai.async_block_till_done()
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 1

    mock_ituran.get_vehicles.side_effect = None
    await mock_config_entry.runtime_data.async_refresh()
    await menuai.async_block_till_done()
    device_entries = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )

    assert len(device_entries) == 1
