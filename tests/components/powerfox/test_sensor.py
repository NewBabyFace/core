"""Test the sensors provided by the Powerfox integration."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from powerfox import PowerfoxConnectionError
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_all_sensors(
    menuai: menuai,
    mock_powerfox_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Powerfox sensors."""
    with patch("menuai.components.powerfox.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_update_failed(
    menuai: menuai,
    mock_powerfox_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test entities become unavailable after failed update."""
    await setup_integration(menuai, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert menuai.states.get("sensor.poweropti_energy_usage").state is not None

    mock_powerfox_client.device.side_effect = PowerfoxConnectionError
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.poweropti_energy_usage").state == STATE_UNAVAILABLE
