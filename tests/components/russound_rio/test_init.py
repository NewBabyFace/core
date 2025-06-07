"""Tests for the Russound RIO integration."""

from unittest.mock import AsyncMock, Mock

from aiorussound.models import CallbackType
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.russound_rio.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import mock_state_update, setup_integration

from tests.common import MockConfigEntry


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_russound_client: AsyncMock,
) -> None:
    """Test the Cambridge Audio configuration entry not ready."""
    mock_russound_client.connect.side_effect = TimeoutError
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    mock_russound_client.connect = AsyncMock(return_value=True)


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_russound_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry integration."""
    await setup_integration(menuai, mock_config_entry)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.unique_id)}
    )
    assert device_entry is not None
    assert device_entry == snapshot


async def test_disconnect_reconnect_log(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_russound_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test device registry integration."""
    await setup_integration(menuai, mock_config_entry)

    mock_russound_client.is_connected = Mock(return_value=False)
    await mock_state_update(mock_russound_client, CallbackType.CONNECTION)
    assert "Disconnected from device at 192.168.20.75" in caplog.text

    mock_russound_client.is_connected = Mock(return_value=True)
    await mock_state_update(mock_russound_client, CallbackType.CONNECTION)
    assert "Reconnected to device at 192.168.20.75" in caplog.text
