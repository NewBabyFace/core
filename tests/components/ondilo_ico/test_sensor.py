"""Test Ondilo ICO integration sensors."""

from typing import Any
from unittest.mock import MagicMock, patch

from ondilo import OndiloError
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensors(
    menuai: menuai,
    mock_ondilo_client: MagicMock,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that I can get all pools data when no error."""
    with patch("menuai.components.ondilo_ico.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, config_entry, mock_ondilo_client)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_no_ico_for_one_pool(
    menuai: menuai,
    mock_ondilo_client: MagicMock,
    config_entry: MockConfigEntry,
    two_pools: list[dict[str, Any]],
    ico_details2: dict[str, Any],
    last_measures: list[dict[str, Any]],
) -> None:
    """Test if an ICO is not attached to a pool, then no sensor for that pool is created."""
    mock_ondilo_client.get_pools.return_value = two_pools
    mock_ondilo_client.get_ICO_details.side_effect = [None, ico_details2]

    await setup_integration(menuai, config_entry, mock_ondilo_client)
    # Only the second pool is created
    assert len(menuai.states.async_all()) == 7
    assert menuai.states.get("sensor.pool_1_temperature") is None
    state = menuai.states.get("sensor.pool_2_rssi")
    assert state is not None
    assert state.state == next(
        str(item["value"]) for item in last_measures if item["data_type"] == "rssi"
    )


async def test_error_retrieving_ico(
    menuai: menuai,
    mock_ondilo_client: MagicMock,
    config_entry: MockConfigEntry,
    pool1: dict[str, Any],
) -> None:
    """Test if there's an error retrieving ICO data, then no sensor is created."""
    mock_ondilo_client.get_pools.return_value = pool1
    mock_ondilo_client.get_ICO_details.side_effect = OndiloError(400, "error")

    await setup_integration(menuai, config_entry, mock_ondilo_client)

    # No sensor should be created
    assert len(menuai.states.async_all()) == 0


async def test_error_retrieving_measures(
    menuai: menuai,
    mock_ondilo_client: MagicMock,
    config_entry: MockConfigEntry,
    pool1: dict[str, Any],
    ico_details1: dict[str, Any],
) -> None:
    """Test if there's an error retrieving measures of ICO, then no sensor is created."""
    mock_ondilo_client.get_pools.return_value = pool1
    mock_ondilo_client.get_ICO_details.return_value = ico_details1
    mock_ondilo_client.get_last_pool_measures.side_effect = OndiloError(400, "error")

    await setup_integration(menuai, config_entry, mock_ondilo_client)

    # No sensor should be created
    assert len(menuai.states.async_all()) == 0
