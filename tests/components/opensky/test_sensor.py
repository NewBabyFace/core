"""OpenSky sensor tests."""

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from python_opensky import StatesResponse
from syrupy.assertion import SnapshotAssertion

from menuai.components.opensky.const import (
    DOMAIN,
    EVENT_OPENSKY_ENTRY,
    EVENT_OPENSKY_EXIT,
)
from menuai.core import Event, menuai

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
)


async def test_sensor(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    opensky_client: AsyncMock,
) -> None:
    """Test setup sensor."""
    await setup_integration(menuai, config_entry)

    state = menuai.states.get("sensor.opensky")
    assert state == snapshot
    events = []

    async def event_listener(event: Event) -> None:
        events.append(event)

    menuai.bus.async_listen(EVENT_OPENSKY_ENTRY, event_listener)
    menuai.bus.async_listen(EVENT_OPENSKY_EXIT, event_listener)
    assert events == []


async def test_sensor_altitude(
    menuai: menuai,
    config_entry_altitude: MockConfigEntry,
    opensky_client: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup sensor with a set altitude."""
    await setup_integration(menuai, config_entry_altitude)

    state = menuai.states.get("sensor.opensky")
    assert state == snapshot


async def test_sensor_updating(
    menuai: menuai,
    config_entry: MockConfigEntry,
    opensky_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test updating sensor."""
    await setup_integration(menuai, config_entry)

    events = []

    async def event_listener(event: Event) -> None:
        events.append(event)

    menuai.bus.async_listen(EVENT_OPENSKY_ENTRY, event_listener)
    menuai.bus.async_listen(EVENT_OPENSKY_EXIT, event_listener)

    async def skip_time_and_check_events() -> None:
        freezer.tick(timedelta(minutes=15))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        assert events == snapshot

    opensky_client.get_states.return_value = StatesResponse.from_api(
        await async_load_json_object_fixture(menuai, "states_1.json", DOMAIN)
    )
    await skip_time_and_check_events()
    opensky_client.get_states.return_value = StatesResponse.from_api(
        await async_load_json_object_fixture(menuai, "states.json", DOMAIN)
    )
    await skip_time_and_check_events()
