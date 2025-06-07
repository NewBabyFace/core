"""Tests for Vodafone Station sensor platform."""

from unittest.mock import AsyncMock, patch

from aiovodafone import CannotAuthenticate
from aiovodafone.exceptions import AlreadyLogged, CannotConnect
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.vodafone_station.const import LINE_TYPES, SCAN_INTERVAL
from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch(
        "menuai.components.vodafone_station.PLATFORMS", [Platform.SENSOR]
    ):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("connection_type", "index"),
    [
        ("dsl_ipaddr", 0),
        ("fiber_ipaddr", 1),
        ("vf_internet_key_ip_addr", 2),
    ],
)
async def test_active_connection_type(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
    connection_type: str,
    index: int,
) -> None:
    """Test device connection type."""
    await setup_integration(menuai, mock_config_entry)

    active_connection_entity = "sensor.vodafone_station_m123456789_active_connection"

    assert (state := menuai.states.get(active_connection_entity))
    assert state.state == STATE_UNKNOWN

    mock_vodafone_station_router.get_sensor_data.return_value[connection_type] = (
        "1.1.1.1"
    )

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(active_connection_entity))
    assert state.state == LINE_TYPES[index]


@pytest.mark.freeze_time("2023-12-02T13:00:00+00:00")
async def test_uptime(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test device uptime shift."""
    await setup_integration(menuai, mock_config_entry)

    uptime = "2024-11-19T20:19:00+00:00"
    uptime_entity = "sensor.vodafone_station_m123456789_uptime"

    assert (state := menuai.states.get(uptime_entity))
    assert state.state == uptime

    mock_vodafone_station_router.get_sensor_data.return_value["sys_uptime"] = "12:17:23"

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get(uptime_entity))
    assert state.state == uptime


@pytest.mark.parametrize(
    "side_effect",
    [
        CannotConnect,
        CannotAuthenticate,
        AlreadyLogged,
        ConnectionResetError,
    ],
)
async def test_coordinator_client_connector_error(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_vodafone_station_router: AsyncMock,
    mock_config_entry: MockConfigEntry,
    side_effect: Exception,
) -> None:
    """Test ClientConnectorError on coordinator update."""
    await setup_integration(menuai, mock_config_entry)

    mock_vodafone_station_router.get_devices_data.side_effect = side_effect
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert (state := menuai.states.get("sensor.vodafone_station_m123456789_uptime"))
    assert state.state == STATE_UNAVAILABLE
