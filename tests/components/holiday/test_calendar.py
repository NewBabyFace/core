"""Tests for calendar platform of Holiday integration."""

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.calendar import (
    DOMAIN as CALENDAR_DOMAIN,
    SERVICE_GET_EVENTS,
)
from menuai.components.holiday.const import CONF_PROVINCE, DOMAIN
from menuai.const import CONF_COUNTRY
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.parametrize(
    "time_zone", ["Asia/Tokyo", "Europe/Berlin", "America/Chicago", "US/Hawaii"]
)
async def test_holiday_calendar_entity(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    time_zone: str,
) -> None:
    """Test HolidayCalendarEntity functionality."""
    await menuai.config.async_set_time_zone(time_zone)
    zone = await dt_util.async_get_time_zone(time_zone)
    freezer.move_to(datetime(2023, 1, 1, 0, 1, 1, tzinfo=zone))  # New Years Day

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "US", CONF_PROVINCE: "AK"},
        title="United States, AK",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await async_setup_component(menuai, "calendar", {})
    await menuai.async_block_till_done()

    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.united_states_ak",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.united_states_ak": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "New Year's Day",
                    "location": "United States, AK",
                }
            ]
        }
    }

    state = menuai.states.get("calendar.united_states_ak")
    assert state is not None
    assert state.state == "on"

    freezer.move_to(
        datetime(2023, 1, 2, 0, 1, 1, tzinfo=zone)
    )  # Day after New Years Day

    state = menuai.states.get("calendar.united_states_ak")
    assert state is not None
    assert state.state == "on"

    # Test holidays for the next year
    freezer.move_to(datetime(2023, 12, 31, 12, tzinfo=zone))

    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.united_states_ak",
            "end_date_time": dt_util.now() + timedelta(days=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.united_states_ak": {
            "events": [
                {
                    "start": "2024-01-01",
                    "end": "2024-01-02",
                    "summary": "New Year's Day",
                    "location": "United States, AK",
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "time_zone", ["Asia/Tokyo", "Europe/Berlin", "America/Chicago", "US/Hawaii"]
)
async def test_default_language(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    time_zone: str,
) -> None:
    """Test default language."""
    await menuai.config.async_set_time_zone(time_zone)
    zone = await dt_util.async_get_time_zone(time_zone)
    freezer.move_to(datetime(2023, 1, 1, 12, tzinfo=zone))

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "FR", CONF_PROVINCE: "BL"},
        title="France, BL",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Test French calendar with English language
    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.france_bl",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.france_bl": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "New Year's Day",
                    "location": "France, BL",
                }
            ]
        }
    }

    # Test French calendar with French language
    menuai.config.language = "fr"

    await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.france_bl",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.france_bl": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "Jour de l'an",
                    "location": "France, BL",
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "time_zone", ["Asia/Tokyo", "Europe/Berlin", "America/Chicago", "US/Hawaii"]
)
async def test_no_language(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    time_zone: str,
) -> None:
    """Test language defaults to English if language not exist."""
    await menuai.config.async_set_time_zone(time_zone)
    zone = await dt_util.async_get_time_zone(time_zone)
    freezer.move_to(datetime(2023, 1, 1, 12, tzinfo=zone))

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "AL"},
        title="Albania",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.albania",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.albania": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "New Year's Day",
                    "location": "Albania",
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "time_zone", ["Asia/Tokyo", "Europe/Berlin", "America/Chicago", "US/Hawaii"]
)
async def test_no_next_event(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    time_zone: str,
) -> None:
    """Test if there is no next event."""
    await menuai.config.async_set_time_zone(time_zone)
    zone = await dt_util.async_get_time_zone(time_zone)
    freezer.move_to(datetime(2023, 1, 1, 12, tzinfo=zone))

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "DE"},
        title="Germany",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Move time to out of reach
    freezer.move_to(datetime(dt_util.now().year + 5, 1, 1, 12, tzinfo=zone))
    async_fire_time_changed(menuai)

    state = menuai.states.get("calendar.germany")
    assert state is not None
    assert state.state == "off"
    assert state.attributes == {"friendly_name": "Germany"}


@pytest.mark.parametrize(
    "time_zone", ["Asia/Tokyo", "Europe/Berlin", "America/Chicago", "US/Hawaii"]
)
async def test_language_not_exist(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    time_zone: str,
) -> None:
    """Test when language doesn't exist it will fallback to country default language."""
    await menuai.config.async_set_time_zone(time_zone)
    zone = await dt_util.async_get_time_zone(time_zone)

    menuai.config.language = "nb"  # Norweigan language "Norks bokmål"
    menuai.config.country = "NO"

    freezer.move_to(datetime(2023, 1, 1, 12, tzinfo=zone))

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "NO"},
        title="Norge",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("calendar.norge")
    assert state is not None
    assert state.state == "on"
    assert state.attributes == {
        "friendly_name": "Norge",
        "all_day": True,
        "description": "",
        "end_time": "2023-01-02 00:00:00",
        "location": "Norge",
        "message": "Første nyttårsdag",
        "start_time": "2023-01-01 00:00:00",
    }

    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.norge",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.norge": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "Første nyttårsdag",
                    "location": "Norge",
                }
            ]
        }
    }

    # Test with English as exist as optional language for Norway
    menuai.config.language = "en"
    menuai.config.country = "NO"
    await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()
    response = await menuai.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": "calendar.norge",
            "end_date_time": dt_util.now() + timedelta(hours=1),
        },
        blocking=True,
        return_response=True,
    )
    assert response == {
        "calendar.norge": {
            "events": [
                {
                    "start": "2023-01-01",
                    "end": "2023-01-02",
                    "summary": "New Year's Day",
                    "location": "Norge",
                }
            ]
        }
    }
