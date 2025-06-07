"""Tests for the MotionMount Entity base."""

from unittest.mock import MagicMock

from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.device_registry import format_mac

from . import ZEROCONF_NAME

from tests.common import MockConfigEntry


async def test_entity_rename(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_motionmount: MagicMock,
) -> None:
    """Tests the state attributes."""
    mock_config_entry.add_to_menuai(menuai)

    mock_motionmount.is_authenticated = True
    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    await menuai.async_block_till_done()

    mac = format_mac(mock_motionmount.mac.hex())
    device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mac)}
    )
    assert device
    assert device.name == ZEROCONF_NAME

    # Simulate the user changed the name of the device
    mock_motionmount.name = "Blub"

    for callback in mock_motionmount.add_listener.call_args_list:
        callback[0][0]()
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, mac)}
    )
    assert device
    assert device.name == "Blub"
