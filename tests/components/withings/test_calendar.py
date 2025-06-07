"""Tests for the Withings calendar."""

from datetime import date, timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai

from . import load_workout_fixture, setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.typing import ClientSessionGenerator


async def test_api_calendar(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test the API returns the calendar."""
    await setup_integration(menuai, polling_config_entry, False)

    client = await menuai_client()
    response = await client.get("/api/calendars")
    assert response.status == HTTPStatus.OK
    data = await response.json()
    assert data == snapshot


async def test_api_events(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test the Withings calendar view."""
    await setup_integration(menuai, polling_config_entry, False)

    client = await menuai_client()
    response = await client.get(
        "/api/calendars/calendar.henk_workouts?start=2023-08-01&end=2023-11-01"
    )
    assert withings.get_workouts_in_period.called == 1
    assert withings.get_workouts_in_period.call_args_list[1].args == (
        date(2023, 8, 1),
        date(2023, 11, 1),
    )
    assert response.status == HTTPStatus.OK
    events = await response.json()
    assert events == snapshot


async def test_calendar_created_when_workouts_available(
    menuai: menuai,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    menuai_client: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the calendar is only created when workouts are available."""
    withings.get_workouts_in_period.return_value = []
    await setup_integration(menuai, polling_config_entry, False)

    assert menuai.states.get("calendar.henk_workouts") is None

    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("calendar.henk_workouts") is None

    withings.get_workouts_in_period.return_value = load_workout_fixture()

    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("calendar.henk_workouts")
