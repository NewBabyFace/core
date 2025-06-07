"""Test the ESPHome bluetooth integration."""

from unittest.mock import patch

from menuai.components import bluetooth
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .conftest import MockESPHomeDevice


async def test_bluetooth_connect_with_raw_adv(
    menuai: menuai, mock_bluetooth_entry_with_raw_adv: MockESPHomeDevice
) -> None:
    """Test bluetooth connect with raw advertisements."""
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner is not None
    assert scanner.connectable is True
    assert scanner.scanning is True
    assert scanner.connector.can_connect() is False  # no connection slots
    await mock_bluetooth_entry_with_raw_adv.mock_disconnect(True)
    await menuai.async_block_till_done()

    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner is None
    await mock_bluetooth_entry_with_raw_adv.mock_connect()
    await menuai.async_block_till_done()
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner.scanning is True


async def test_bluetooth_connect_with_legacy_adv(
    menuai: menuai, mock_bluetooth_entry_with_legacy_adv: MockESPHomeDevice
) -> None:
    """Test bluetooth connect with legacy advertisements."""
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner is not None
    assert scanner.connectable is True
    assert scanner.scanning is True
    assert scanner.connector.can_connect() is False  # no connection slots
    await mock_bluetooth_entry_with_legacy_adv.mock_disconnect(True)
    await menuai.async_block_till_done()

    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner is None
    await mock_bluetooth_entry_with_legacy_adv.mock_connect()
    await menuai.async_block_till_done()
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner.scanning is True


async def test_bluetooth_device_linked_via_device(
    menuai: menuai,
    mock_bluetooth_entry_with_raw_adv: MockESPHomeDevice,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the Bluetooth device is linked to the ESPHome device."""
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner.connectable is True
    entry = menuai.config_entries.async_entry_for_domain_unique_id(
        "bluetooth", "AA:BB:CC:DD:EE:FC"
    )
    assert entry is not None
    esp_device = device_registry.async_get_device(
        connections={
            (
                dr.CONNECTION_NETWORK_MAC,
                mock_bluetooth_entry_with_raw_adv.device_info.mac_address,
            )
        }
    )
    assert esp_device is not None
    device = device_registry.async_get_device(
        connections={(dr.CONNECTION_BLUETOOTH, "AA:BB:CC:DD:EE:FC")}
    )
    assert device is not None
    assert device.via_device_id == esp_device.id


async def test_bluetooth_cleanup_on_remove_entry(
    menuai: menuai, mock_bluetooth_entry_with_raw_adv: MockESPHomeDevice
) -> None:
    """Test bluetooth is cleaned up on entry removal."""
    scanner = bluetooth.async_scanner_by_source(menuai, "AA:BB:CC:DD:EE:FC")
    assert scanner.connectable is True
    await menuai.config_entries.async_unload(
        mock_bluetooth_entry_with_raw_adv.entry.entry_id
    )

    with patch("menuai.components.esphome.async_remove_scanner") as remove_mock:
        await menuai.config_entries.async_remove(
            mock_bluetooth_entry_with_raw_adv.entry.entry_id
        )
        await menuai.async_block_till_done()

    remove_mock.assert_called_once_with(menuai, scanner.source)
