"""Tests for the Steam component."""

import steam

from menuai.components.steam_online.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import create_entry, patch_interface


async def test_setup(menuai: menuai) -> None:
    """Test unload."""
    entry = create_entry(menuai)
    with patch_interface():
        await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_auth_failed(menuai: menuai) -> None:
    """Test that it throws ConfigEntryAuthFailed when authentication fails."""
    entry = create_entry(menuai)
    with patch_interface() as interface:
        interface.side_effect = steam.api.HTTPError("401")
        await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert not menuai.data.get(DOMAIN)


async def test_device_info(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test device info."""
    entry = create_entry(menuai)
    with patch_interface():
        await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.configuration_url == "https://store.steampowered.com"
    assert device.entry_type == dr.DeviceEntryType.SERVICE
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == DEFAULT_NAME
    assert device.name == DEFAULT_NAME
