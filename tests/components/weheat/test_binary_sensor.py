"""Tests for the weheat sensor platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion
from weheat.abstractions.discovery import HeatPumpDiscovery

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_weheat_discover: AsyncMock,
    mock_weheat_heat_pump: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.weheat.PLATFORMS", [Platform.BINARY_SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_create_binary_entities(
    menuai: menuai,
    mock_weheat_discover: AsyncMock,
    mock_weheat_heat_pump: AsyncMock,
    mock_heat_pump_info: HeatPumpDiscovery.HeatPumpInfo,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test creating entities."""
    mock_weheat_discover.return_value = [mock_heat_pump_info]

    with patch("menuai.components.weheat.PLATFORMS", [Platform.BINARY_SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 4
