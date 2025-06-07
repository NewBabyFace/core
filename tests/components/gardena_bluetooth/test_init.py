"""Test the Gardena Bluetooth setup."""

from datetime import timedelta
from unittest.mock import Mock

from gardena_bluetooth.const import Battery
from syrupy.assertion import SnapshotAssertion

from menuai.components.gardena_bluetooth import DeviceUnavailable
from menuai.components.gardena_bluetooth.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.util import utcnow

from . import WATER_TIMER_SERVICE_INFO

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_setup(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mock_entry: MockConfigEntry,
    mock_read_char_raw: dict[str, bytes],
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup creates expected devices."""

    mock_read_char_raw[Battery.battery_level.uuid] = Battery.battery_level.encode(100)

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_entry.state is ConfigEntryState.LOADED

    device = device_registry.async_get_device(
        identifiers={(DOMAIN, WATER_TIMER_SERVICE_INFO.address)}
    )
    assert device == snapshot


async def test_setup_retry(
    menuai: menuai, mock_entry: MockConfigEntry, mock_client: Mock
) -> None:
    """Test setup creates expected devices."""

    original_read_char = mock_client.read_char.side_effect
    mock_client.read_char.side_effect = DeviceUnavailable
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_entry.state is ConfigEntryState.SETUP_RETRY

    mock_client.read_char.side_effect = original_read_char

    async_fire_time_changed(menuai, utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert mock_entry.state is ConfigEntryState.LOADED
