"""Tests for the Sky Remote component."""

from unittest.mock import AsyncMock

from skyboxremote import SkyBoxConnectionError

from menuai.components.sky_remote.const import DEFAULT_PORT, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_mock_entry

from tests.common import MockConfigEntry


async def test_setup_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_remote_control,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test successful setup of entry."""
    await setup_mock_entry(menuai, mock_config_entry)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    mock_remote_control.assert_called_once_with("example.com", DEFAULT_PORT)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.entry_id)}
    )
    assert device_entry is not None
    assert device_entry.name == "example.com"


async def test_setup_unconnectable_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_remote_control,
) -> None:
    """Test unsuccessful setup of entry."""
    mock_remote_control._instance_mock.check_connectable = AsyncMock(
        side_effect=SkyBoxConnectionError()
    )

    await setup_mock_entry(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_remote_control
) -> None:
    """Test unload an entry."""
    await setup_mock_entry(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
