"""Tests for the Slide Local integration."""

from unittest.mock import AsyncMock

from goslideapi.goslideapi import ClientConnectionError
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_platform

from tests.common import MockConfigEntry


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_slide_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry integration."""
    await setup_platform(menuai, mock_config_entry, [Platform.COVER])
    device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, "1234567890ab")}
    )
    assert device_entry is not None
    assert device_entry == snapshot


async def test_raise_config_entry_not_ready_when_offline(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_slide_api: AsyncMock,
) -> None:
    """Config entry state is SETUP_RETRY when slide is offline."""

    mock_slide_api.slide_info.side_effect = [ClientConnectionError, None]

    await setup_platform(menuai, mock_config_entry, [Platform.COVER])
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    assert len(menuai.config_entries.flow.async_progress()) == 0


async def test_raise_config_entry_not_ready_when_empty_data(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_slide_api: AsyncMock,
) -> None:
    """Config entry state is SETUP_RETRY when slide is offline."""

    mock_slide_api.slide_info.return_value = None

    await setup_platform(menuai, mock_config_entry, [Platform.COVER])
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    assert len(menuai.config_entries.flow.async_progress()) == 0
