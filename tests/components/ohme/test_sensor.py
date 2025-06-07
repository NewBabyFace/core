"""Tests for sensors."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from ohme import ApiException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Ohme sensors."""
    with patch("menuai.components.ohme.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_sensors_unavailable(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test that sensors show as unavailable after a coordinator failure."""
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("sensor.ohme_home_pro_energy")
    assert state.state == "1.0"

    mock_client.async_get_charge_session.side_effect = ApiException
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.ohme_home_pro_energy")
    assert state.state == STATE_UNAVAILABLE

    mock_client.async_get_charge_session.side_effect = None
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.ohme_home_pro_energy")
    assert state.state == "1.0"
