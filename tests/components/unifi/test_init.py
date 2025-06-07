"""Test UniFi Network integration setup process."""

from typing import Any
from unittest.mock import patch

from aiounifi.models.message import MessageKey
import pytest

from menuai.components import unifi
from menuai.components.unifi.const import (
    CONF_ALLOW_BANDWIDTH_SENSORS,
    CONF_ALLOW_UPTIME_SENSORS,
    CONF_TRACK_CLIENTS,
    CONF_TRACK_DEVICES,
)
from menuai.components.unifi.errors import AuthenticationRequired, CannotConnect
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from .conftest import (
    DEFAULT_CONFIG_ENTRY_ID,
    ConfigEntryFactoryType,
    WebsocketMessageMock,
)

from tests.common import flush_store
from tests.typing import WebSocketGenerator


async def test_setup_entry_fails_config_entry_not_ready(
    menuai: menuai, config_entry_factory: ConfigEntryFactoryType
) -> None:
    """Failed authentication trigger a reauthentication flow."""
    with patch(
        "menuai.components.unifi.get_unifi_api",
        side_effect=CannotConnect,
    ):
        config_entry = await config_entry_factory()

    assert config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_setup_entry_fails_trigger_reauth_flow(
    menuai: menuai, config_entry_factory: ConfigEntryFactoryType
) -> None:
    """Failed authentication trigger a reauthentication flow."""
    with (
        patch(
            "menuai.components.unifi.get_unifi_api",
            side_effect=AuthenticationRequired,
        ),
        patch.object(menuai.config_entries.flow, "async_init") as mock_flow_init,
    ):
        config_entry = await config_entry_factory()
        mock_flow_init.assert_called_once()

    assert config_entry.state == ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(
    "client_payload",
    [
        [
            {
                "hostname": "client_1",
                "ip": "10.0.0.1",
                "is_wired": False,
                "mac": "00:00:00:00:00:01",
            },
            {
                "hostname": "client_2",
                "ip": "10.0.0.2",
                "is_wired": False,
                "mac": "00:00:00:00:00:02",
            },
        ]
    ],
)
async def test_wireless_clients(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    config_entry_factory: ConfigEntryFactoryType,
) -> None:
    """Verify wireless clients class."""
    menuai_storage[unifi.STORAGE_KEY] = {
        "version": unifi.STORAGE_VERSION,
        "data": {
            DEFAULT_CONFIG_ENTRY_ID: {
                "wireless_devices": ["00:00:00:00:00:00", "00:00:00:00:00:01"]
            }
        },
    }

    await config_entry_factory()
    await flush_store(menuai.data[unifi.UNIFI_WIRELESS_CLIENTS]._store)

    assert sorted(menuai_storage[unifi.STORAGE_KEY]["data"]["wireless_clients"]) == [
        "00:00:00:00:00:00",
        "00:00:00:00:00:01",
        "00:00:00:00:00:02",
    ]


@pytest.mark.parametrize(
    "client_payload",
    [
        [
            {
                "hostname": "Wired client",
                "is_wired": True,
                "mac": "00:00:00:00:00:01",
                "oui": "Producer",
                "wired-rx_bytes": 1234000000,
                "wired-tx_bytes": 5678000000,
                "uptime": 1600094505,
            },
            {
                "is_wired": False,
                "mac": "00:00:00:00:00:02",
                "name": "Wireless client",
                "oui": "Producer",
                "rx_bytes": 2345000000,
                "tx_bytes": 6789000000,
                "uptime": 60,
            },
        ]
    ],
)
@pytest.mark.parametrize(
    "device_payload",
    [
        [
            {
                "board_rev": 3,
                "device_id": "mock-id",
                "has_fan": True,
                "fan_level": 0,
                "ip": "10.0.1.1",
                "last_seen": 1562600145,
                "mac": "00:00:00:00:01:01",
                "model": "US16P150",
                "name": "Device 1",
                "next_interval": 20,
                "overheating": True,
                "state": 1,
                "type": "usw",
                "upgradable": True,
                "version": "4.0.42.10433",
            }
        ]
    ],
)
@pytest.mark.parametrize(
    "config_entry_options",
    [
        {
            CONF_ALLOW_BANDWIDTH_SENSORS: True,
            CONF_ALLOW_UPTIME_SENSORS: True,
            CONF_TRACK_CLIENTS: True,
            CONF_TRACK_DEVICES: True,
        }
    ],
)
async def test_remove_config_entry_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    config_entry_factory: ConfigEntryFactoryType,
    client_payload: list[dict[str, Any]],
    device_payload: list[dict[str, Any]],
    mock_websocket_message: WebsocketMessageMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Verify removing a device manually."""
    config_entry = await config_entry_factory()

    assert await async_setup_component(menuai, "config", {})
    ws_client = await menuai_ws_client(menuai)

    # Try to remove an active client from UI: not allowed
    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, client_payload[0]["mac"])}
    )
    response = await ws_client.remove_device(device_entry.id, config_entry.entry_id)
    assert not response["success"]
    assert device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, client_payload[0]["mac"])}
    )

    # Try to remove an active device from UI: not allowed
    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, device_payload[0]["mac"])}
    )
    response = await ws_client.remove_device(device_entry.id, config_entry.entry_id)
    assert not response["success"]
    assert device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, device_payload[0]["mac"])}
    )

    # Remove a client from Unifi API
    mock_websocket_message(message=MessageKey.CLIENT_REMOVED, data=[client_payload[1]])
    await menuai.async_block_till_done()

    # Try to remove an inactive client from UI: allowed
    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, client_payload[1]["mac"])}
    )
    response = await ws_client.remove_device(device_entry.id, config_entry.entry_id)
    assert response["success"]
    assert not device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, client_payload[1]["mac"])}
    )
