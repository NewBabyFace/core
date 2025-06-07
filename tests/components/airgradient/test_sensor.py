"""Tests for the AirGradient sensor platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from airgradient import AirGradientError, Measures
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.airgradient.const import DOMAIN
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_fixture,
    snapshot_platform,
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    airgradient_devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.airgradient.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_create_entities(
    menuai: menuai,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test creating entities."""
    mock_airgradient_client.get_current_measures.return_value = Measures.from_json(
        await async_load_fixture(menuai, "measures_after_boot.json", DOMAIN)
    )
    with patch("menuai.components.airgradient.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    assert len(menuai.states.async_all()) == 0
    mock_airgradient_client.get_current_measures.return_value = Measures.from_json(
        await async_load_fixture(menuai, "current_measures_indoor.json", DOMAIN)
    )
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 9


async def test_connection_error(
    menuai: menuai,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection error."""
    await setup_integration(menuai, mock_config_entry)

    mock_airgradient_client.get_current_measures.side_effect = AirGradientError()
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.airgradient_humidity").state == STATE_UNAVAILABLE
