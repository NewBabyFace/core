"""Tests for the Epic Games Store calendars."""

from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory

from menuai.components.calendar import (
    DOMAIN as CALENDAR_DOMAIN,
    EVENT_END_DATETIME,
    EVENT_START_DATETIME,
    SERVICE_GET_EVENTS,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.util import dt as dt_util

from .common import setup_platform

from tests.common import async_fire_time_changed


async def test_setup_component(menuai: menuai, service_multiple: Mock) -> None:
    """Test setup component."""
    await setup_platform(menuai, CALENDAR_DOMAIN)

    state = menuai.states.get("calendar.epic_games_store_discount_games")
    assert state.name == "Epic Games Store Discount games"
    state = menuai.states.get("calendar.epic_games_store_free_games")
    assert state.name == "Epic Games Store Free games"


async def test_discount_games(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_multiple: Mock,
) -> None:
    """Test discount games calendar."""
    freezer.move_to("2022-10-15T00:00:00.000Z")

    await setup_platform(menuai, CALENDAR_DOMAIN)

    state = menuai.states.get("calendar.epic_games_store_discount_games")
    assert state.state == STATE_OFF

    freezer.move_to("2022-10-30T00:00:00.000Z")
    async_fire_time_changed(menuai)

    state = menuai.states.get("calendar.epic_games_store_discount_games")
    assert state.state == STATE_ON

    cal_attrs = dict(state.attributes)
    assert cal_attrs == {
        "friendly_name": "Epic Games Store Discount games",
        "message": "Shadow of the Tomb Raider: Definitive Edition",
        "all_day": False,
        "start_time": "2022-10-18 08:00:00",
        "end_time": "2022-11-01 08:00:00",
        "location": "",
        "description": "In Shadow of the Tomb Raider Definitive Edition experience the final chapter of Lara\u2019s origin as she is forged into the Tomb Raider she is destined to be.\n\nhttps://store.epicgames.com/fr/p/shadow-of-the-tomb-raider",
    }


async def test_free_games(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_multiple: Mock,
) -> None:
    """Test free games calendar."""
    freezer.move_to("2022-10-30T00:00:00.000Z")

    await setup_platform(menuai, CALENDAR_DOMAIN)

    state = menuai.states.get("calendar.epic_games_store_free_games")
    assert state.state == STATE_ON

    cal_attrs = dict(state.attributes)
    assert cal_attrs == {
        "friendly_name": "Epic Games Store Free games",
        "message": "Warhammer 40,000: Mechanicus - Standard Edition",
        "all_day": False,
        "start_time": "2022-10-27 08:00:00",
        "end_time": "2022-11-03 08:00:00",
        "location": "",
        "description": "Take control of the most technologically advanced army in the Imperium - The Adeptus Mechanicus. Your every decision will weigh heavily on the outcome of the mission, in this turn-based tactical game. Will you be blessed by the Omnissiah?\n\nhttps://store.epicgames.com/fr/p/warhammer-mechanicus-0e4b71",
    }


async def test_attribute_not_found(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_attribute_not_found: Mock,
) -> None:
    """Test setup calendars with attribute not found error."""
    freezer.move_to("2023-10-12T00:00:00.000Z")

    await setup_platform(menuai, CALENDAR_DOMAIN)

    state = menuai.states.get("calendar.epic_games_store_discount_games")
    assert state.name == "Epic Games Store Discount games"
    state = menuai.states.get("calendar.epic_games_store_free_games")
    assert state.name == "Epic Games Store Free games"
    assert state.state == STATE_ON


async def test_christmas_special(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_christmas_special: Mock,
) -> None:
    """Test setup calendars with Christmas special case."""
    freezer.move_to("2023-12-28T00:00:00.000Z")

    await setup_platform(menuai, CALENDAR_DOMAIN)

    state = menuai.states.get("calendar.epic_games_store_discount_games")
    assert state.name == "Epic Games Store Discount games"
    assert state.state == STATE_OFF

    state = menuai.states.get("calendar.epic_games_store_free_games")
    assert state.name == "Epic Games Store Free games"
    assert state.state == STATE_ON


async def test_get_events(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_multiple: Mock,
) -> None:
    """Test setup component with calendars."""
    freezer.move_to("2022-10-30T00:00:00.000Z")

    await setup_platform(menuai, CALENDAR_DOMAIN)

    # 1 week in range of data
    result = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            ATTR_ENTITY_ID: ["calendar.epic_games_store_discount_games"],
            EVENT_START_DATETIME: dt_util.parse_datetime("2022-10-20T00:00:00.000Z"),
            EVENT_END_DATETIME: dt_util.parse_datetime("2022-10-27T00:00:00.000Z"),
        },
        blocking=True,
        return_response=True,
    )

    assert len(result["calendar.epic_games_store_discount_games"]["events"]) == 3

    # 1 week out of range of data
    result = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            ATTR_ENTITY_ID: ["calendar.epic_games_store_discount_games"],
            EVENT_START_DATETIME: dt_util.parse_datetime("1970-01-01T00:00:00.000Z"),
            EVENT_END_DATETIME: dt_util.parse_datetime("1970-01-08T00:00:00.000Z"),
        },
        blocking=True,
        return_response=True,
    )

    assert len(result["calendar.epic_games_store_discount_games"]["events"]) == 0
