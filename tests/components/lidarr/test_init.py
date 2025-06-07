"""Test Lidarr integration."""

from menuai.components.lidarr.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .conftest import ComponentSetup


async def test_setup(
    menuai: menuai, setup_integration: ComponentSetup, connection
) -> None:
    """Test setup."""
    await setup_integration()
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_not_ready(
    menuai: menuai, setup_integration: ComponentSetup, cannot_connect
) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    await setup_integration()
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_auth_failed(
    menuai: menuai, setup_integration: ComponentSetup, invalid_auth
) -> None:
    """Test that it throws ConfigEntryAuthFailed when authentication fails."""
    await setup_integration()
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert not menuai.data.get(DOMAIN)


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    setup_integration: ComponentSetup,
    connection,
) -> None:
    """Test device info."""
    await setup_integration()
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    await menuai.async_block_till_done()
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.configuration_url == "http://127.0.0.1:8668"
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == DEFAULT_NAME
    assert device.name == "Mock Title"
    assert device.sw_version == "10.0.0.34882"
