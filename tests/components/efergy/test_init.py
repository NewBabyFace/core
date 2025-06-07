"""Test Efergy integration."""

from pyefergy import exceptions

from menuai.components.efergy.const import DEFAULT_NAME, DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import _patch_efergy_status, create_entry, init_integration, setup_platform

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Test unload."""
    entry = await init_integration(menuai, aioclient_mock)
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = create_entry(menuai)
    with _patch_efergy_status() as efergymock:
        efergymock.side_effect = (exceptions.ConnectError, exceptions.DataError)
        await menuai.config_entries.async_setup(entry.entry_id)
        assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
        assert entry.state is ConfigEntryState.SETUP_RETRY
        assert not menuai.data.get(DOMAIN)


async def test_async_setup_entry_auth_failed(menuai: menuai) -> None:
    """Test that it throws ConfigEntryAuthFailed when authentication fails."""
    entry = create_entry(menuai)
    with _patch_efergy_status() as efergymock:
        efergymock.side_effect = exceptions.InvalidAuth
        await menuai.config_entries.async_setup(entry.entry_id)
        assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
        assert entry.state is ConfigEntryState.SETUP_ERROR
        assert not menuai.data.get(DOMAIN)


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test device info."""
    entry = await setup_platform(menuai, aioclient_mock, SENSOR_DOMAIN)

    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.configuration_url == "https://engage.efergy.com/user/login"
    assert device.connections == {("mac", "ff:ff:ff:ff:ff:ff")}
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == DEFAULT_NAME
    assert device.model == "EEEHub"
    assert device.name == DEFAULT_NAME
    assert device.sw_version == "2.3.7"
