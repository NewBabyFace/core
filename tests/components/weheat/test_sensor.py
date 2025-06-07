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
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_weheat_discover: AsyncMock,
    mock_weheat_heat_pump: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.weheat.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(("has_dhw", "nr_of_entities"), [(False, 16), (True, 19)])
async def test_create_entities(
    menuai: menuai,
    mock_weheat_discover: AsyncMock,
    mock_weheat_heat_pump: AsyncMock,
    mock_heat_pump_info: HeatPumpDiscovery.HeatPumpInfo,
    mock_config_entry: MockConfigEntry,
    has_dhw: bool,
    nr_of_entities: int,
) -> None:
    """Test creating entities."""
    mock_heat_pump_info.has_dhw = has_dhw
    mock_weheat_discover.return_value = [mock_heat_pump_info]

    with patch("menuai.components.weheat.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == nr_of_entities
