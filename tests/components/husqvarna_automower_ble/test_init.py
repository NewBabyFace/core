"""Test the Husqvarna Automower Bluetooth setup."""

from unittest.mock import Mock

from bleak import BleakError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.husqvarna_automower_ble.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import AUTOMOWER_SERVICE_INFO

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_automower_client")


async def test_setup(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup creates expected devices."""

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{AUTOMOWER_SERVICE_INFO.address}_1197489078")}
    )

    assert device_entry == snapshot


async def test_setup_retry_connect(
    menuai: menuai,
    mock_automower_client: Mock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup creates expected devices."""

    mock_automower_client.connect.return_value = False

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_failed_connect(
    menuai: menuai,
    mock_automower_client: Mock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup creates expected devices."""

    mock_automower_client.connect.side_effect = BleakError

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
