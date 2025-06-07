"""Tests for the MotionMount init."""

from unittest.mock import MagicMock

from menuai.components.motionmount import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.device_registry import format_mac

from tests.common import MockConfigEntry


async def test_setup_entry_with_mac(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    mac = format_mac(mock_motionmount.mac.hex())
    device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mac)}
    )
    assert device
    assert device.name == mock_config_entry.title


async def test_setup_entry_without_mac(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    mock_motionmount.mac = b"\x00\x00\x00\x00\x00\x00"

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.entry_id)}
    )
    assert device
    assert device.name == mock_config_entry.title


async def test_setup_entry_failed_connect(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    mock_motionmount.connect.side_effect = TimeoutError()
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_wrong_device(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    mock_motionmount.mac = b"\x00\x00\x00\x00\x00\x01"
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_no_pin(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    mock_motionmount.is_authenticated = False
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(mock_config_entry.async_get_active_flows(menuai, sources={SOURCE_REAUTH}))


async def test_setup_entry_wrong_pin(
    menuai: menuai,
    mock_config_entry_with_pin: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry_with_pin.add_to_menuai(menuai)

    mock_motionmount.is_authenticated = False
    assert not await menuai.config_entries.async_setup(
        mock_config_entry_with_pin.entry_id
    )

    assert mock_config_entry_with_pin.state is ConfigEntryState.SETUP_ERROR
    assert any(
        mock_config_entry_with_pin.async_get_active_flows(menuai, sources={SOURCE_REAUTH})
    )


async def test_unload_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Test entries are unloaded correctly."""
    mock_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_motionmount.disconnect.call_count == 1
