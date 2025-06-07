"""Test for Trafikverket Train component Init."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytrafikverket import (
    InvalidAuthentication,
    NoTrainStationFound,
    StationInfoModel,
    TrainStopModel,
    UnknownError,
)
from syrupy.assertion import SnapshotAssertion

from menuai.components.trafikverket_train.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, SOURCE_USER, ConfigEntryState
from menuai.core import menuai
from menuai.helpers.entity_registry import EntityRegistry

from . import ENTRY_CONFIG, OPTIONS_CONFIG

from tests.common import MockConfigEntry


async def test_unload_entry(
    menuai: menuai, get_trains: list[TrainStopModel]
) -> None:
    """Test unload an entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        entry_id="1",
        version=2,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_station_from_signature",
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            return_value=get_trains,
        ) as mock_tv_train,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert len(mock_tv_train.mock_calls) == 1

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_auth_failed(
    menuai: menuai,
    get_trains: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test authentication failed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        entry_id="1",
        version=2,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_station_from_signature",
        side_effect=InvalidAuthentication,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR

    active_flows = entry.async_get_active_flows(menuai, (SOURCE_REAUTH))
    for flow in active_flows:
        assert flow == snapshot


async def test_no_stations(
    menuai: menuai,
    get_trains: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test stations are missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        entry_id="1",
        version=2,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_station_from_signature",
        side_effect=NoTrainStationFound,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_migrate_entity_unique_id(
    menuai: menuai,
    get_trains: list[TrainStopModel],
    snapshot: SnapshotAssertion,
    entity_registry: EntityRegistry,
) -> None:
    """Test migration of entity unique id in old format."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        entry_id="1",
        version=2,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    entity = entity_registry.async_get_or_create(
        DOMAIN,
        "sensor",
        "incorrect_unique_id",
        config_entry=entry,
        original_name="Stockholm C to Uppsala C",
    )

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_station_from_signature",
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            return_value=get_trains,
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    entity = entity_registry.async_get(entity.entity_id)
    assert entity.unique_id == f"{entry.entry_id}-departure_time"


async def test_migrate_entry(
    menuai: menuai,
    get_trains: list[TrainStopModel],
    get_train_stations: list[StationInfoModel],
) -> None:
    """Test migrate entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        version=1,
        minor_version=1,
        entry_id="1",
        unique_id="321",
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_station_from_signature",
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_search_train_stations",
            side_effect=get_train_stations,
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            return_value=get_trains,
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    assert entry.version == 2
    assert entry.minor_version == 1
    # Migration to version 2.1 changed from/to to use station signatures
    assert entry.data == {
        "api_key": "1234567890",
        "from": "Cst",
        "to": "U",
        "time": None,
        "weekday": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "name": "Stockholm C to Uppsala C",
    }
    # Migration to version 1.2 removed unique_id
    assert entry.unique_id is None


async def test_migrate_entry_from_future_version_fails(
    menuai: menuai,
    get_trains: list[TrainStopModel],
) -> None:
    """Test migrate entry from future version fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        version=3,
        minor_version=1,
        entry_id="1",
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR


@pytest.mark.parametrize(
    ("side_effect"),
    [
        (InvalidAuthentication),
        (NoTrainStationFound),
        (UnknownError),
        (Exception),
    ],
)
async def test_migrate_entry_fails(menuai: menuai, side_effect: Exception) -> None:
    """Test migrate entry fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        version=1,
        minor_version=1,
        entry_id="1",
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.trafikverket_train.config_flow.TrafikverketTrain.async_search_train_stations",
            side_effect=side_effect(),
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_migrate_entry_fails_multiple_stations(
    menuai: menuai,
    get_multiple_train_stations: list[StationInfoModel],
) -> None:
    """Test migrate entry fails on multiple stations found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        version=1,
        minor_version=1,
        entry_id="1",
        unique_id="321",
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_search_train_stations",
            side_effect=get_multiple_train_stations,
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR
