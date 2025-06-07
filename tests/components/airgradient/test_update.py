"""Tests for the AirGradient update platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.airgradient.PLATFORMS", [Platform.UPDATE]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_update_mechanism(
    menuai: menuai,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test update entity."""
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("update.airgradient_firmware")
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "3.1.1"
    assert state.attributes["latest_version"] == "3.1.4"
    mock_airgradient_client.get_latest_firmware_version.assert_called_once()
    mock_airgradient_client.get_latest_firmware_version.reset_mock()

    mock_airgradient_client.get_current_measures.return_value.firmware_version = "3.1.4"

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("update.airgradient_firmware")
    assert state.state == STATE_OFF
    assert state.attributes["installed_version"] == "3.1.4"
    assert state.attributes["latest_version"] == "3.1.4"

    mock_airgradient_client.get_latest_firmware_version.return_value = "3.1.5"

    freezer.tick(timedelta(minutes=59))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    mock_airgradient_client.get_latest_firmware_version.assert_called_once()
    state = menuai.states.get("update.airgradient_firmware")
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "3.1.4"
    assert state.attributes["latest_version"] == "3.1.5"
