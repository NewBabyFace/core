"""Tests for the devolo Home Control integration."""

from unittest.mock import patch

from devolo_home_control_api.exceptions.gateway import GatewayOfflineError
import pytest

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.devolo_home_control.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import configure_integration
from .mocks import HomeControlMock, HomeControlMockBinarySensor

from tests.typing import WebSocketGenerator


@pytest.mark.usefixtures("mock_zeroconf")
async def test_setup_entry(menuai: menuai) -> None:
    """Test setup entry."""
    entry = configure_integration(menuai)
    with patch("menuai.components.devolo_home_control.HomeControl"):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize("credentials_valid", [False])
async def test_setup_entry_credentials_invalid(menuai: menuai) -> None:
    """Test setup entry fails if credentials are invalid."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize("maintenance", [True])
async def test_setup_entry_maintenance(menuai: menuai) -> None:
    """Test setup entry fails if mydevolo is in maintenance mode."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_zeroconf")
async def test_setup_gateway_offline(menuai: menuai) -> None:
    """Test setup entry fails on gateway offline."""
    entry = configure_integration(menuai)
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=GatewayOfflineError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload entry."""
    entry = configure_integration(menuai)
    with patch("menuai.components.devolo_home_control.HomeControl"):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        await menuai.config_entries.async_unload(entry.entry_id)
        assert entry.state is ConfigEntryState.NOT_LOADED


async def test_home_assistant_stop(menuai: menuai) -> None:
    """Test MenuAI stop."""
    entry = configure_integration(menuai)
    test_gateway = HomeControlMock()
    test_gateway2 = HomeControlMock()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, test_gateway2],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        menuai.bus.async_fire(EVENT_menuai_STOP)
        await menuai.async_block_till_done()
        assert test_gateway.websocket_disconnect.called
        assert test_gateway2.websocket_disconnect.called


async def test_remove_device(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test removing a device."""
    assert await async_setup_component(menuai, "config", {})
    entry = configure_integration(menuai)
    test_gateway = HomeControlMockBinarySensor()
    with patch(
        "menuai.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        device_entry = device_registry.async_get_device(identifiers={(DOMAIN, "Test")})
        assert device_entry

        client = await menuai_ws_client(menuai)
        response = await client.remove_device(device_entry.id, entry.entry_id)
        assert response["success"]
        assert device_registry.async_get_device(identifiers={(DOMAIN, "Test")}) is None
        assert menuai.states.get(f"{BINARY_SENSOR_DOMAIN}.test") is None
