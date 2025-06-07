"""Test Goal Zero integration."""

from datetime import timedelta
from unittest.mock import patch

from goalzero import exceptions

from menuai.components.goalzero.const import DEFAULT_NAME, DOMAIN, MANUFACTURER
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.util import dt as dt_util

from . import CONF_DATA, async_init_integration, create_entry

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup_config_and_unload(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test Goal Zero setup and unload."""
    entry = await async_init_integration(menuai, aioclient_mock)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_setup_config_entry_incorrectly_formatted_mac(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the mac address formatting is corrected."""
    entry = await async_init_integration(menuai, aioclient_mock, skip_setup=True)
    menuai.config_entries.async_update_entry(entry, unique_id="AABBCCDDEEFF")
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"


async def test_async_setup_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = create_entry(menuai)
    with patch(
        "menuai.components.goalzero.Yeti.init_connect",
        side_effect=exceptions.ConnectError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_update_failed(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test data update failure."""
    await async_init_integration(menuai, aioclient_mock)
    assert menuai.states.get(f"switch.{DEFAULT_NAME}_ac_port_status").state == STATE_ON
    with patch(
        "menuai.components.goalzero.Yeti.get_state",
        side_effect=exceptions.ConnectError,
    ) as updater:
        next_update = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done()
        updater.assert_called_once()
        state = menuai.states.get(f"switch.{DEFAULT_NAME}_ac_port_status")
        assert state.state == STATE_UNAVAILABLE


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test device info."""
    entry = await async_init_integration(menuai, aioclient_mock)

    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.connections == {("mac", "12:34:56:78:90:12")}
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == MANUFACTURER
    assert device.model == "Yeti 1400"
    assert device.name == DEFAULT_NAME
    assert device.sw_version == "1.5.7"
