"""Tests for the steamist component."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from discovery30303 import AIODiscovery30303
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components import steamist
from menuai.components.steamist.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_NAME
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import (
    DEFAULT_ENTRY_DATA,
    DEVICE_30303,
    DEVICE_IP_ADDRESS,
    DEVICE_MODEL,
    DEVICE_NAME,
    FORMATTED_MAC_ADDRESS,
    MOCK_ASYNC_GET_STATUS_ACTIVE,
    _async_setup_entry_with_status,
    _patch_status,
)

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture
def mock_single_broadcast_address():
    """Mock network's async_async_get_ipv4_broadcast_addresses."""
    with patch(
        "menuai.components.network.async_get_ipv4_broadcast_addresses",
        return_value={"10.255.255.255"},
    ):
        yield


async def test_config_entry_reload(menuai: menuai) -> None:
    """Test that a config entry can be reloaded."""
    _, config_entry = await _async_setup_entry_with_status(
        menuai, MOCK_ASYNC_GET_STATUS_ACTIVE
    )
    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_config_entry_retry_later(menuai: menuai) -> None:
    """Test that a config entry retry on connection error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1"},
    )
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.steamist.Steamist.async_get_status",
        side_effect=TimeoutError,
    ):
        await async_setup_component(menuai, steamist.DOMAIN, {steamist.DOMAIN: {}})
        await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_entry_fills_unique_id_with_directed_discovery(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test that the unique id is added if its missing via directed (not broadcast) discovery."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: DEVICE_IP_ADDRESS}, unique_id=None
    )
    config_entry.add_to_menuai(menuai)
    last_address = None

    async def _async_scan(*args, address=None, **kwargs):
        # Only return discovery results when doing directed discovery
        nonlocal last_address
        last_address = address

    @property
    def found_devices(self):
        nonlocal last_address
        return [DEVICE_30303] if last_address == DEVICE_IP_ADDRESS else []

    mock_aio_discovery = MagicMock(auto_spec=AIODiscovery30303)
    mock_aio_discovery.async_scan = _async_scan
    type(mock_aio_discovery).found_devices = found_devices

    with (
        _patch_status(MOCK_ASYNC_GET_STATUS_ACTIVE),
        patch(
            "menuai.components.steamist.discovery.AIODiscovery30303",
            return_value=mock_aio_discovery,
        ),
    ):
        await async_setup_component(menuai, steamist.DOMAIN, {steamist.DOMAIN: {}})
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED

    assert config_entry.unique_id == FORMATTED_MAC_ADDRESS
    assert config_entry.data[CONF_NAME] == DEVICE_NAME
    assert config_entry.title == DEVICE_NAME

    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, FORMATTED_MAC_ADDRESS)}
    )
    assert isinstance(device_entry, dr.DeviceEntry)
    assert device_entry.name == DEVICE_NAME
    assert device_entry.model == DEVICE_MODEL


@pytest.mark.usefixtures("mock_single_broadcast_address")
async def test_discovery_happens_at_interval(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test that discovery happens at interval."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=DEFAULT_ENTRY_DATA, unique_id=FORMATTED_MAC_ADDRESS
    )
    config_entry.add_to_menuai(menuai)
    mock_aio_discovery = MagicMock(auto_spec=AIODiscovery30303)
    mock_aio_discovery.async_scan = AsyncMock()
    with (
        patch(
            "menuai.components.steamist.discovery.AIODiscovery30303",
            return_value=mock_aio_discovery,
        ),
        _patch_status(MOCK_ASYNC_GET_STATUS_ACTIVE),
    ):
        await async_setup_component(menuai, steamist.DOMAIN, {steamist.DOMAIN: {}})
        await menuai.async_block_till_done(wait_background_tasks=True)

        assert len(mock_aio_discovery.async_scan.mock_calls) == 2

        freezer.move_to(utcnow() + steamist.DISCOVERY_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(mock_aio_discovery.async_scan.mock_calls) == 3
