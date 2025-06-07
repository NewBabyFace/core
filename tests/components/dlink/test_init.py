"""Test D-Link Smart Plug setup."""

from unittest.mock import MagicMock

from menuai.components.dlink.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .conftest import CONF_DATA, ComponentSetup, patch_setup

from tests.common import MockConfigEntry


async def test_setup_config_and_unload(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test setup and unload."""
    await setup_integration()

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_legacy_setup_config_and_unload(
    menuai: menuai, setup_integration_legacy: ComponentSetup
) -> None:
    """Test legacy setup and unload."""
    await setup_integration_legacy()

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_not_ready(
    menuai: menuai,
    config_entry_with_uid: MockConfigEntry,
    mocked_plug_legacy_no_auth: MagicMock,
) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during legacy setup."""
    with patch_setup(mocked_plug_legacy_no_auth):
        await menuai.config_entries.async_setup(config_entry_with_uid.entry_id)
    assert config_entry_with_uid.state is ConfigEntryState.SETUP_RETRY


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    setup_integration: ComponentSetup,
) -> None:
    """Test device info."""
    await setup_integration()

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.connections == {("mac", "aa:bb:cc:dd:ee:ff")}
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == "D-Link"
    assert device.model == "DSP-W215"
    assert device.name == "Mock Title"
