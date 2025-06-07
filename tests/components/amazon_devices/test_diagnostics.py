"""Tests for Amazon Devices diagnostics platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.amazon_devices.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration
from .const import TEST_SERIAL_NUMBER

from tests.common import MockConfigEntry
from tests.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Amazon config entry diagnostics."""
    await setup_integration(menuai, mock_config_entry)

    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, mock_config_entry
    ) == snapshot(
        exclude=props(
            "entry_id",
            "created_at",
            "modified_at",
        )
    )


async def test_device_diagnostics(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test Amazon device diagnostics."""
    await setup_integration(menuai, mock_config_entry)

    device = device_registry.async_get_device(
        identifiers={(DOMAIN, TEST_SERIAL_NUMBER)}
    )
    assert device, repr(device_registry.devices)

    assert await get_diagnostics_for_device(
        menuai, menuai_client, mock_config_entry, device
    ) == snapshot(
        exclude=props(
            "entry_id",
            "created_at",
            "modified_at",
        )
    )
