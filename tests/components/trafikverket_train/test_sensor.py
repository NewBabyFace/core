"""The test for the Trafikverket train sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytrafikverket.exceptions import InvalidAuthentication, NoTrainAnnouncementFound
from pytrafikverket.models import TrainStopModel
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import SOURCE_REAUTH, ConfigEntry
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from tests.common import async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_next(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    load_int: ConfigEntry,
    get_trains_next: list[TrainStopModel],
    get_train_stop: TrainStopModel,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Trafikverket Train sensor."""
    for entity in (
        "sensor.stockholm_c_to_uppsala_c_departure_time",
        "sensor.stockholm_c_to_uppsala_c_departure_state",
        "sensor.stockholm_c_to_uppsala_c_actual_time",
        "sensor.stockholm_c_to_uppsala_c_other_information",
        "sensor.stockholm_c_to_uppsala_c_departure_time_next",
        "sensor.stockholm_c_to_uppsala_c_departure_time_next_after",
    ):
        state = menuai.states.get(entity)
        assert state == snapshot

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            return_value=get_trains_next,
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_stop",
            return_value=get_train_stop,
        ),
    ):
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    for entity in (
        "sensor.stockholm_c_to_uppsala_c_departure_time",
        "sensor.stockholm_c_to_uppsala_c_departure_state",
        "sensor.stockholm_c_to_uppsala_c_actual_time",
        "sensor.stockholm_c_to_uppsala_c_other_information",
        "sensor.stockholm_c_to_uppsala_c_departure_time_next",
        "sensor.stockholm_c_to_uppsala_c_departure_time_next_after",
    ):
        state = menuai.states.get(entity)
        assert state == snapshot


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_single_stop(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    load_int: ConfigEntry,
    get_trains_next: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Trafikverket Train sensor."""
    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")

    assert state.state == "2023-05-01T11:00:00+00:00"

    assert state == snapshot


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_update_auth_failure(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    load_int: ConfigEntry,
    get_trains_next: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Trafikverket Train sensor with authentication update failure."""
    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == "2023-05-01T11:00:00+00:00"

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            side_effect=InvalidAuthentication,
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_stop",
            side_effect=InvalidAuthentication,
        ),
    ):
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == STATE_UNAVAILABLE
    active_flows = load_int.async_get_active_flows(menuai, (SOURCE_REAUTH))
    for flow in active_flows:
        assert flow == snapshot


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_update_failure(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    load_int: ConfigEntry,
    get_trains_next: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Trafikverket Train sensor with update failure."""
    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == "2023-05-01T11:00:00+00:00"

    with (
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_next_train_stops",
            side_effect=NoTrainAnnouncementFound,
        ),
        patch(
            "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_stop",
            side_effect=NoTrainAnnouncementFound,
        ),
    ):
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_update_failure_no_state(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    load_int: ConfigEntry,
    get_trains_next: list[TrainStopModel],
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Trafikverket Train sensor with update failure from empty state."""
    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == "2023-05-01T11:00:00+00:00"

    with patch(
        "menuai.components.trafikverket_train.coordinator.TrafikverketTrain.async_get_train_stop",
        return_value=None,
    ):
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.stockholm_c_to_uppsala_c_departure_time_2")
    assert state.state == STATE_UNAVAILABLE
