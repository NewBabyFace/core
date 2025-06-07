"""Tests for the swiss_public_transport sensor platform."""

import json
from unittest.mock import AsyncMock, patch

from opendata_transport.exceptions import (
    OpendataTransportConnectionError,
    OpendataTransportError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.swiss_public_transport.const import (
    DEFAULT_UPDATE_TIME,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_fixture,
    snapshot_platform,
)
from tests.test_config_entries import FrozenDateTimeFactory


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_opendata_client: AsyncMock,
    swiss_public_transport_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.cookidoo.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, swiss_public_transport_config_entry)

    assert swiss_public_transport_config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(
        menuai, entity_registry, snapshot, swiss_public_transport_config_entry.entry_id
    )


@pytest.mark.parametrize(
    ("raise_error"),
    [OpendataTransportConnectionError, OpendataTransportError],
)
async def test_fetching_data(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_opendata_client: AsyncMock,
    swiss_public_transport_config_entry: MockConfigEntry,
    raise_error: Exception,
) -> None:
    """Test fetching data."""
    await setup_integration(menuai, swiss_public_transport_config_entry)

    assert swiss_public_transport_config_entry.state is ConfigEntryState.LOADED

    mock_opendata_client.async_get_data.assert_called()

    assert mock_opendata_client.async_get_data.call_count == 2

    assert len(menuai.states.async_all(SENSOR_DOMAIN)) == 8

    assert (
        menuai.states.get("sensor.zurich_bern_departure").state
        == "2024-01-06T17:03:00+00:00"
    )
    assert (
        menuai.states.get("sensor.zurich_bern_departure_1").state
        == "2024-01-06T17:04:00+00:00"
    )
    assert (
        menuai.states.get("sensor.zurich_bern_departure_2").state
        == "2024-01-06T17:05:00+00:00"
    )
    assert (
        round(float(menuai.states.get("sensor.zurich_bern_trip_duration").state), 3)
        == 0.003
    )
    assert menuai.states.get("sensor.zurich_bern_platform").state == "0"
    assert menuai.states.get("sensor.zurich_bern_transfers").state == "0"
    assert menuai.states.get("sensor.zurich_bern_delay").state == "0"
    assert menuai.states.get("sensor.zurich_bern_line").state == "T10"

    # Set new data and verify it
    mock_opendata_client.connections = json.loads(
        await async_load_fixture(menuai, "connections.json", DOMAIN)
    )[3:6]
    freezer.tick(DEFAULT_UPDATE_TIME)
    async_fire_time_changed(menuai)
    assert mock_opendata_client.async_get_data.call_count == 3
    assert (
        menuai.states.get("sensor.zurich_bern_departure").state
        == "2024-01-06T17:06:00+00:00"
    )

    # Simulate fetch exception
    mock_opendata_client.async_get_data.side_effect = raise_error
    freezer.tick(DEFAULT_UPDATE_TIME)
    async_fire_time_changed(menuai)
    assert mock_opendata_client.async_get_data.call_count == 4
    assert menuai.states.get("sensor.zurich_bern_departure").state == "unavailable"

    # Recover and fetch new data again
    mock_opendata_client.async_get_data.side_effect = None
    mock_opendata_client.connections = json.loads(
        await async_load_fixture(menuai, "connections.json", DOMAIN)
    )[6:9]
    freezer.tick(DEFAULT_UPDATE_TIME)
    async_fire_time_changed(menuai)
    assert mock_opendata_client.async_get_data.call_count == 5
    assert (
        menuai.states.get("sensor.zurich_bern_departure").state
        == "2024-01-06T17:09:00+00:00"
    )


@pytest.mark.parametrize(
    ("raise_error", "state"),
    [
        (OpendataTransportConnectionError, ConfigEntryState.SETUP_RETRY),
        (OpendataTransportError, ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_fetching_data_setup_exception(
    menuai: menuai,
    mock_opendata_client: AsyncMock,
    swiss_public_transport_config_entry: MockConfigEntry,
    raise_error: Exception,
    state: ConfigEntryState,
) -> None:
    """Test fetching data with setup exception."""

    mock_opendata_client.async_get_data.side_effect = raise_error
    await setup_integration(menuai, swiss_public_transport_config_entry)

    assert swiss_public_transport_config_entry.state is state
