"""Test Hydrawise binary_sensor."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError
from freezegun.api import FrozenDateTimeFactory
from pydrawise.schema import Controller
from syrupy.assertion import SnapshotAssertion

from menuai.components.hydrawise.const import MAIN_SCAN_INTERVAL
from menuai.const import STATE_OFF, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_all_binary_sensors(
    menuai: menuai,
    mock_add_config_entry: Callable[[], Awaitable[MockConfigEntry]],
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that all binary sensors are working."""
    with patch(
        "menuai.components.hydrawise.PLATFORMS",
        [Platform.BINARY_SENSOR],
    ):
        config_entry = await mock_add_config_entry()
        await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_update_data_fails(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that no data from the API sets the correct connectivity."""
    # Make the coordinator refresh data.
    mock_pydrawise.get_user.reset_mock(return_value=True)
    mock_pydrawise.get_user.side_effect = ClientError
    mock_pydrawise.get_water_use_summary.side_effect = ClientError
    freezer.tick(MAIN_SCAN_INTERVAL + timedelta(seconds=30))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    connectivity = menuai.states.get("binary_sensor.home_controller_connectivity")
    assert connectivity is not None
    assert connectivity.state == STATE_OFF


async def test_controller_offline(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    freezer: FrozenDateTimeFactory,
    controller: Controller,
) -> None:
    """Test the binary_sensor for the controller being online."""
    # Make the coordinator refresh data.
    controller.online = False
    freezer.tick(MAIN_SCAN_INTERVAL + timedelta(seconds=30))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    connectivity = menuai.states.get("binary_sensor.home_controller_connectivity")
    assert connectivity
    assert connectivity.state == STATE_OFF
