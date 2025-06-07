"""Tests for the Tile integration."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.tile.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration

from tests.common import MockConfigEntry


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_pytile: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry integration."""
    await setup_integration(menuai, mock_config_entry)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, "19264d2dffdbca32")}
    )
    assert device_entry is not None
    assert device_entry == snapshot
