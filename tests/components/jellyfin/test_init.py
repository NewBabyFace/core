"""Tests for the Jellyfin integration."""

from unittest.mock import MagicMock

from menuai.components.jellyfin.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import async_load_json_fixture

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_jellyfin: MagicMock,
    mock_client: MagicMock,
) -> None:
    """Test the Jellyfin configuration entry not ready."""
    mock_client.auth.connect_to_address.return_value = await async_load_json_fixture(
        menuai,
        "auth-connect-address-failure.json",
    )

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_invalid_auth(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_jellyfin: MagicMock,
    mock_client: MagicMock,
) -> None:
    """Test the Jellyfin integration handling invalid credentials."""
    mock_client.auth.connect_to_address.return_value = await async_load_json_fixture(
        menuai,
        "auth-connect-address.json",
    )
    mock_client.auth.login.return_value = await async_load_json_fixture(
        menuai,
        "auth-login-failure.json",
    )

    mock_config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_jellyfin: MagicMock,
) -> None:
    """Test the Jellyfin configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device_remove_devices(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
    mock_jellyfin: MagicMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test we can only remove a device that no longer exists."""
    assert await async_setup_component(menuai, "config", {})

    mock_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    device_entry = device_registry.async_get_device(
        identifiers={
            (
                DOMAIN,
                "DEVICE-UUID",
            )
        },
    )
    client = await menuai_ws_client(menuai)
    response = await client.remove_device(device_entry.id, mock_config_entry.entry_id)
    assert not response["success"]

    old_device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "OLD-DEVICE-UUID")},
    )
    response = await client.remove_device(
        old_device_entry.id, mock_config_entry.entry_id
    )
    assert response["success"]
