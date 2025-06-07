"""Test sensor of Airly integration."""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from airly.exceptions import AirlyError
from syrupy.assertion import SnapshotAssertion

from menuai.components.airly.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import API_POINT_URL, init_integration

from tests.common import async_fire_time_changed, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_sensor(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states of the sensor."""
    with patch("menuai.components.airly.PLATFORMS", [Platform.SENSOR]):
        entry = await init_integration(menuai, aioclient_mock)

    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert (state := menuai.states.get(entity_entry.entity_id))
        assert state == snapshot(name=f"{entity_entry.entity_id}-state")


async def test_availability(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Ensure that we mark the entities unavailable correctly when service is offline."""
    await init_integration(menuai, aioclient_mock)

    state = menuai.states.get("sensor.home_humidity")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "68.35"

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        API_POINT_URL, exc=AirlyError(HTTPStatus.NOT_FOUND, {"message": "Not found"})
    )
    future = utcnow() + timedelta(minutes=60)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.home_humidity")
    assert state
    assert state.state == STATE_UNAVAILABLE

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        API_POINT_URL, text=await async_load_fixture(menuai, "valid_station.json", DOMAIN)
    )
    future = utcnow() + timedelta(minutes=120)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.home_humidity")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "68.35"


async def test_manual_update_entity(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test manual update entity via service menuai/update_entity."""
    await init_integration(menuai, aioclient_mock)

    call_count = aioclient_mock.call_count
    await async_setup_component(menuai, "menuai", {})
    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {ATTR_ENTITY_ID: ["sensor.home_humidity"]},
        blocking=True,
    )

    assert aioclient_mock.call_count == call_count + 1
