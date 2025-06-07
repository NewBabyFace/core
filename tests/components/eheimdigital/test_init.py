"""Tests for the init module."""

from unittest.mock import MagicMock

from eheimdigital.types import EheimDeviceType

from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from .conftest import init_integration

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


async def test_remove_device(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test removing a device."""
    assert await async_setup_component(menuai, "config", {})

    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:01", EheimDeviceType.VERSION_EHEIM_CLASSIC_LED_CTRL_PLUS_E
    )
    await menuai.async_block_till_done()

    mac_address: str = eheimdigital_hub_mock.return_value.main.mac_address

    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac_address)},
    )
    assert device_entry is not None

    menuai_client = await menuai_ws_client(menuai)

    # Do not allow to delete a connected device
    response = await menuai_client.remove_device(
        device_entry.id, mock_config_entry.entry_id
    )
    assert not response["success"]

    eheimdigital_hub_mock.return_value.devices = {}

    # Allow to delete a not connected device
    response = await menuai_client.remove_device(
        device_entry.id, mock_config_entry.entry_id
    )
    assert response["success"]
