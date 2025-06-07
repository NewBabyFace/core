"""Tests for the binary sensor platform of the Pterodactyl integration."""

from collections.abc import Generator
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from requests.exceptions import ConnectionError
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_ON, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("mock_pterodactyl")
async def test_binary_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test binary sensor."""
    with patch(
        "menuai.components.pterodactyl._PLATFORMS", [Platform.BINARY_SENSOR]
    ):
        mock_config_entry = await setup_integration(menuai, mock_config_entry)

        assert len(menuai.states.async_all(Platform.BINARY_SENSOR)) == 2
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry.entry_id
        )


@pytest.mark.usefixtures("mock_pterodactyl")
async def test_binary_sensor_update(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test binary sensor update."""
    await setup_integration(menuai, mock_config_entry)

    freezer.tick(timedelta(seconds=90))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all(Platform.BINARY_SENSOR)) == 2
    assert (
        menuai.states.get(f"{Platform.BINARY_SENSOR}.test_server_1_status").state
        == STATE_ON
    )
    assert (
        menuai.states.get(f"{Platform.BINARY_SENSOR}.test_server_2_status").state
        == STATE_ON
    )


async def test_binary_sensor_update_failure(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pterodactyl: Generator[AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test failed binary sensor update."""
    await setup_integration(menuai, mock_config_entry)

    mock_pterodactyl.client.servers.get_server.side_effect = ConnectionError(
        "Simulated connection error"
    )

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert len(menuai.states.async_all(Platform.BINARY_SENSOR)) == 2
    assert (
        menuai.states.get(f"{Platform.BINARY_SENSOR}.test_server_1_status").state
        == STATE_UNAVAILABLE
    )
    assert (
        menuai.states.get(f"{Platform.BINARY_SENSOR}.test_server_2_status").state
        == STATE_UNAVAILABLE
    )
