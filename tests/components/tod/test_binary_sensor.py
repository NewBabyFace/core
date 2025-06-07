"""Test Times of the Day Binary Sensor."""

from datetime import datetime, timedelta, tzinfo

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.sun import get_astral_event_date, get_astral_event_next
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import assert_setup_component, async_fire_time_changed


@pytest.fixture
def menuai_time_zone() -> str:
    """Return default menuai timezone."""
    return "US/Pacific"


@pytest.fixture(autouse=True)
async def setup_fixture(menuai: menuai, menuai_time_zone: str) -> None:
    """Set up things to be run when tests are started."""
    menuai.config.latitude = 50.27583
    menuai.config.longitude = 18.98583
    await menuai.config.async_set_time_zone(menuai_time_zone)


@pytest.fixture
def menuai_tz_info(menuai: menuai) -> tzinfo | None:
    """Return timezone info for the menuai timezone."""
    return dt_util.get_time_zone(menuai.config.time_zone)


async def test_setup(menuai: menuai) -> None:
    """Test the setup."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Early Morning",
                "after": "sunrise",
                "after_offset": "-02:00",
                "before": "7:00",
                "before_offset": "1:00",
            },
            {
                "platform": "tod",
                "name": "Morning",
                "after": "sunrise",
                "before": "12:00",
            },
        ]
    }
    with assert_setup_component(2):
        assert await async_setup_component(menuai, "binary_sensor", config)


async def test_setup_no_sensors(menuai: menuai) -> None:
    """Test setup with no sensors."""
    with assert_setup_component(0):
        assert await async_setup_component(
            menuai, "binary_sensor", {"binary_sensor": {"platform": "tod"}}
        )


@pytest.mark.freeze_time("2019-01-10 18:43:00-08:00")
async def test_in_period_on_start(menuai: menuai) -> None:
    """Test simple setting."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Evening",
                "after": "18:00",
                "before": "22:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.evening")
    assert state.state == STATE_ON


@pytest.mark.freeze_time("2019-01-10 22:30:00-08:00")
async def test_midnight_turnover_before_midnight_inside_period(
    menuai: menuai,
) -> None:
    """Test midnight turnover setting before midnight inside period ."""
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Night", "after": "22:00", "before": "5:00"}
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON


async def test_midnight_turnover_after_midnight_inside_period(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test midnight turnover setting before midnight inside period ."""
    test_time = datetime(2019, 1, 10, 21, 0, 0, tzinfo=menuai_tz_info)
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Night", "after": "22:00", "before": "5:00"}
        ]
    }
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF

    await menuai.async_block_till_done()

    freezer.move_to(test_time + timedelta(hours=1))
    async_fire_time_changed(menuai, dt_util.utcnow())

    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON


@pytest.mark.freeze_time("2019-01-10 20:30:00-08:00")
async def test_midnight_turnover_before_midnight_outside_period(
    menuai: menuai,
) -> None:
    """Test midnight turnover setting before midnight outside period."""
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Night", "after": "22:00", "before": "5:00"}
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF


@pytest.mark.freeze_time("2019-01-10 10:00:00-08:00")
async def test_after_happens_tomorrow(menuai: menuai) -> None:
    """Test when both before and after are in the future, and after is later than before."""
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Night", "after": "23:00", "before": "12:00"}
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON


async def test_midnight_turnover_after_midnight_outside_period(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test midnight turnover setting before midnight inside period ."""
    test_time = datetime(2019, 1, 10, 20, 0, 0, tzinfo=menuai_tz_info)

    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Night", "after": "22:00", "before": "5:00"}
        ]
    }
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF

    switchover_time = datetime(2019, 1, 11, 4, 59, 0, tzinfo=menuai_tz_info)
    freezer.move_to(switchover_time)

    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON

    freezer.move_to(switchover_time + timedelta(minutes=1, seconds=1))

    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF


async def test_from_sunrise_to_sunset(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test period from sunrise to sunset."""
    test_time = datetime(2019, 1, 12, tzinfo=menuai_tz_info)
    sunrise = dt_util.as_local(
        get_astral_event_date(menuai, "sunrise", dt_util.as_utc(test_time))
    )
    sunset = dt_util.as_local(
        get_astral_event_date(menuai, "sunset", dt_util.as_utc(test_time))
    )
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Day",
                "after": "sunrise",
                "before": "sunset",
            }
        ]
    }
    entity_id = "binary_sensor.day"
    freezer.move_to(sunrise + timedelta(seconds=-1))
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunset + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_from_sunset_to_sunrise(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test period from sunset to sunrise."""
    test_time = datetime(2019, 1, 12, tzinfo=menuai_tz_info)
    sunset = dt_util.as_local(get_astral_event_date(menuai, "sunset", test_time))
    sunrise = dt_util.as_local(get_astral_event_next(menuai, "sunrise", sunset))
    # assert sunset == sunrise
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Night",
                "after": "sunset",
                "before": "sunrise",
            }
        ]
    }
    entity_id = "binary_sensor.night"
    freezer.move_to(sunset + timedelta(seconds=-1))
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunset)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset + timedelta(minutes=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise + timedelta(minutes=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise + timedelta(minutes=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_offset(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test offset."""
    after = datetime(2019, 1, 10, 18, 0, 0, tzinfo=menuai_tz_info) + timedelta(
        hours=1, minutes=34
    )

    before = datetime(2019, 1, 10, 22, 0, 0, tzinfo=menuai_tz_info) + timedelta(
        hours=1, minutes=45
    )

    entity_id = "binary_sensor.evening"
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Evening",
                "after": "18:00",
                "after_offset": "1:34",
                "before": "22:00",
                "before_offset": "1:45",
            }
        ]
    }
    freezer.move_to(after + timedelta(seconds=-1))
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(after)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(before + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(before)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(before + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_offset_overnight(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test offset overnight."""
    after = datetime(2019, 1, 10, 18, 0, 0, tzinfo=menuai_tz_info) + timedelta(
        hours=1, minutes=34
    )
    entity_id = "binary_sensor.evening"
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Evening",
                "after": "18:00",
                "after_offset": "1:34",
                "before": "22:00",
                "before_offset": "3:00",
            }
        ]
    }
    freezer.move_to(after + timedelta(seconds=-1))
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(after)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON


async def test_norwegian_case_winter(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test location in Norway where the sun doesn't set in summer."""
    menuai.config.latitude = 69.6
    menuai.config.longitude = 18.8

    test_time = datetime(2010, 1, 1, tzinfo=menuai_tz_info)
    sunrise = dt_util.as_local(
        get_astral_event_next(menuai, "sunrise", dt_util.as_utc(test_time))
    )
    sunset = dt_util.as_local(
        get_astral_event_next(menuai, "sunset", dt_util.as_utc(test_time))
    )
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Day",
                "after": "sunrise",
                "before": "sunset",
            }
        ]
    }
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunset + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_norwegian_case_summer(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test location in Norway where the sun doesn't set in summer."""
    menuai.config.latitude = 69.6
    menuai.config.longitude = 18.8
    menuai.config.elevation = 10.0

    test_time = datetime(2010, 6, 1, tzinfo=menuai_tz_info)

    sunrise = dt_util.as_local(
        get_astral_event_next(menuai, "sunrise", dt_util.as_utc(test_time))
    )
    sunset = dt_util.as_local(
        get_astral_event_next(menuai, "sunset", dt_util.as_utc(sunrise))
    )
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Day",
                "after": "sunrise",
                "before": "sunset",
            }
        ]
    }
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunset + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_sun_offset(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test sun event with offset."""
    test_time = datetime(2019, 1, 12, tzinfo=menuai_tz_info)
    sunrise = dt_util.as_local(
        get_astral_event_date(menuai, "sunrise", dt_util.as_utc(test_time))
        + timedelta(hours=-1, minutes=-30)
    )
    sunset = dt_util.as_local(
        get_astral_event_date(menuai, "sunset", dt_util.as_utc(test_time))
        + timedelta(hours=1, minutes=30)
    )
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Day",
                "after": "sunrise",
                "after_offset": "-1:30",
                "before": "sunset",
                "before_offset": "1:30",
            }
        ]
    }
    entity_id = "binary_sensor.day"
    freezer.move_to(sunrise + timedelta(seconds=-1))
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunrise + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    freezer.move_to(sunset + timedelta(seconds=-1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await menuai.async_block_till_done()

    freezer.move_to(sunset)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    freezer.move_to(sunset + timedelta(seconds=1))
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF

    test_time = test_time + timedelta(days=1)
    sunrise = dt_util.as_local(
        get_astral_event_date(menuai, "sunrise", dt_util.as_utc(test_time))
        + timedelta(hours=-1, minutes=-30)
    )
    freezer.move_to(sunrise)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON


async def test_dst1(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when time falls in non-existent hour. Also check 48 hours later."""
    menuai.config.time_zone = "CET"
    dt_util.set_default_time_zone(dt_util.get_time_zone("CET"))
    test_time1 = datetime(2019, 3, 30, 3, 0, 0, tzinfo=dt_util.get_time_zone("CET"))
    test_time2 = datetime(2019, 3, 31, 3, 0, 0, tzinfo=dt_util.get_time_zone("CET"))
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "2:30", "before": "2:40"}
        ]
    }
    # Test DST #1:
    # after 2019-03-30 03:00 CET the next update should ge scheduled
    # at 2:30am, but on 2019-03-31, that hour does not exist.  That means
    # the start/end will end up happning on the next available second (3am)
    # Essentially, the ToD sensor never turns on that day.
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time1)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["before"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T03:00:00+02:00"
    assert state.state == STATE_OFF

    # But the following day, the sensor should resume it normal operation.
    freezer.move_to(test_time2)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-04-01T02:30:00+02:00"
    assert state.attributes["before"] == "2019-04-01T02:40:00+02:00"
    assert state.attributes["next_update"] == "2019-04-01T02:30:00+02:00"

    assert state.state == STATE_OFF


async def test_dst2(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when there's a time switch in the East."""
    menuai.config.time_zone = "CET"
    dt_util.set_default_time_zone(dt_util.get_time_zone("CET"))
    test_time = datetime(2019, 3, 30, 5, 0, 0, tzinfo=dt_util.get_time_zone("CET"))
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "4:30", "before": "4:40"}
        ]
    }
    # Test DST #2:
    # after 2019-03-30 05:00 CET the next update should ge scheduled
    # at 4:30+02 not 4:30+01
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T04:30:00+02:00"
    assert state.attributes["before"] == "2019-03-31T04:40:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T04:30:00+02:00"
    assert state.state == STATE_OFF


async def test_dst3(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when there's a time switch forward in the West."""
    menuai.config.time_zone = "US/Pacific"
    dt_util.set_default_time_zone(dt_util.get_time_zone("US/Pacific"))
    test_time = datetime(
        2023, 3, 11, 5, 0, 0, tzinfo=dt_util.get_time_zone("US/Pacific")
    )
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "4:30", "before": "4:40"}
        ]
    }
    # Test DST #3:
    # after 2023-03-11 05:00 Pacific the next update should ge scheduled
    # at 4:30-07 not 4:30-08
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2023-03-12T04:30:00-07:00"
    assert state.attributes["before"] == "2023-03-12T04:40:00-07:00"
    assert state.attributes["next_update"] == "2023-03-12T04:30:00-07:00"
    assert state.state == STATE_OFF


async def test_dst4(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when there's a time switch backward in the West."""
    menuai.config.time_zone = "US/Pacific"
    dt_util.set_default_time_zone(dt_util.get_time_zone("US/Pacific"))
    test_time = datetime(
        2023, 11, 4, 5, 0, 0, tzinfo=dt_util.get_time_zone("US/Pacific")
    )
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "4:30", "before": "4:40"}
        ]
    }
    # Test DST #4:
    # after 2023-11-04 05:00 Pacific the next update should ge scheduled
    # at 4:30-08 not 4:30-07
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2023-11-05T04:30:00-08:00"
    assert state.attributes["before"] == "2023-11-05T04:40:00-08:00"
    assert state.attributes["next_update"] == "2023-11-05T04:30:00-08:00"
    assert state.state == STATE_OFF


async def test_dst5(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when end time falls in non-existent hour (1:50am-2:10am)."""
    menuai.config.time_zone = "CET"
    dt_util.set_default_time_zone(dt_util.get_time_zone("CET"))
    test_time1 = datetime(2019, 3, 30, 3, 0, 0, tzinfo=dt_util.get_time_zone("CET"))
    test_time2 = datetime(2019, 3, 31, 1, 51, 0, tzinfo=dt_util.get_time_zone("CET"))
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "1:50", "before": "2:10"}
        ]
    }
    # Test DST #5:
    # Test the case where the end time does not exist (roll out to the next available time)
    # First test before the sensor is turned on
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time1)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T01:50:00+01:00"
    assert state.attributes["before"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T01:50:00+01:00"
    assert state.state == STATE_OFF

    # Seconds, test state when sensor is ON but end time has rolled out to next available time.
    freezer.move_to(test_time2)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T01:50:00+01:00"
    assert state.attributes["before"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T03:00:00+02:00"

    assert state.state == STATE_ON


async def test_dst6(
    menuai: menuai, freezer: FrozenDateTimeFactory, menuai_tz_info
) -> None:
    """Test DST when start time falls in non-existent hour (2:50am 3:10am)."""
    menuai.config.time_zone = "CET"
    dt_util.set_default_time_zone(dt_util.get_time_zone("CET"))
    test_time1 = datetime(2019, 3, 30, 4, 0, 0, tzinfo=dt_util.get_time_zone("CET"))
    test_time2 = datetime(2019, 3, 31, 3, 1, 0, tzinfo=dt_util.get_time_zone("CET"))
    config = {
        "binary_sensor": [
            {"platform": "tod", "name": "Day", "after": "2:50", "before": "3:10"}
        ]
    }
    # Test DST #6:
    # Test the case where the end time does not exist (roll out to the next available time)
    # First test before the sensor is turned on
    entity_id = "binary_sensor.day"
    freezer.move_to(test_time1)
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["before"] == "2019-03-31T03:10:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T03:00:00+02:00"
    assert state.state == STATE_OFF

    # Seconds, test state when sensor is ON but end time has rolled out to next available time.
    freezer.move_to(test_time2)
    async_fire_time_changed(menuai, dt_util.utcnow())
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.attributes["after"] == "2019-03-31T03:00:00+02:00"
    assert state.attributes["before"] == "2019-03-31T03:10:00+02:00"
    assert state.attributes["next_update"] == "2019-03-31T03:10:00+02:00"

    assert state.state == STATE_ON


@pytest.mark.freeze_time("2019-01-10 18:43:00")
@pytest.mark.parametrize("menuai_time_zone", ["UTC"])
async def test_simple_before_after_does_not_loop_utc_not_in_range(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Night",
                "before": "06:00",
                "after": "22:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF
    assert state.attributes["after"] == "2019-01-10T22:00:00+00:00"
    assert state.attributes["before"] == "2019-01-11T06:00:00+00:00"
    assert state.attributes["next_update"] == "2019-01-10T22:00:00+00:00"


@pytest.mark.freeze_time("2019-01-10 22:43:00")
@pytest.mark.parametrize("menuai_time_zone", ["UTC"])
async def test_simple_before_after_does_not_loop_utc_in_range(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Night",
                "before": "06:00",
                "after": "22:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON
    assert state.attributes["after"] == "2019-01-10T22:00:00+00:00"
    assert state.attributes["before"] == "2019-01-11T06:00:00+00:00"
    assert state.attributes["next_update"] == "2019-01-11T06:00:00+00:00"


@pytest.mark.freeze_time("2019-01-11 06:00:00")
@pytest.mark.parametrize("menuai_time_zone", ["UTC"])
async def test_simple_before_after_does_not_loop_utc_fire_at_before(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Night",
                "before": "06:00",
                "after": "22:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_OFF
    assert state.attributes["after"] == "2019-01-11T22:00:00+00:00"
    assert state.attributes["before"] == "2019-01-12T06:00:00+00:00"
    assert state.attributes["next_update"] == "2019-01-11T22:00:00+00:00"


@pytest.mark.freeze_time("2019-01-10 22:00:00")
@pytest.mark.parametrize("menuai_time_zone", ["UTC"])
async def test_simple_before_after_does_not_loop_utc_fire_at_after(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Night",
                "before": "06:00",
                "after": "22:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.night")
    assert state.state == STATE_ON
    assert state.attributes["after"] == "2019-01-10T22:00:00+00:00"
    assert state.attributes["before"] == "2019-01-11T06:00:00+00:00"
    assert state.attributes["next_update"] == "2019-01-11T06:00:00+00:00"


@pytest.mark.freeze_time("2019-01-10 22:00:00")
@pytest.mark.parametrize("menuai_time_zone", ["UTC"])
async def test_simple_before_after_does_not_loop_utc_both_before_now(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Morning",
                "before": "08:00",
                "after": "00:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.morning")
    assert state.state == STATE_OFF
    assert state.attributes["after"] == "2019-01-11T00:00:00+00:00"
    assert state.attributes["before"] == "2019-01-11T08:00:00+00:00"
    assert state.attributes["next_update"] == "2019-01-11T00:00:00+00:00"


@pytest.mark.freeze_time("2019-01-10 17:43:00+01:00")
@pytest.mark.parametrize("menuai_time_zone", ["Europe/Berlin"])
async def test_simple_before_after_does_not_loop_berlin_not_in_range(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Dark",
                "before": "06:00",
                "after": "00:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.dark")
    assert state.state == STATE_OFF
    assert state.attributes["after"] == "2019-01-11T00:00:00+01:00"
    assert state.attributes["before"] == "2019-01-11T06:00:00+01:00"
    assert state.attributes["next_update"] == "2019-01-11T00:00:00+01:00"


@pytest.mark.freeze_time("2019-01-11 00:43:00+01:00")
@pytest.mark.parametrize("menuai_time_zone", ["Europe/Berlin"])
async def test_simple_before_after_does_not_loop_berlin_in_range(
    menuai: menuai,
) -> None:
    """Test simple before after."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Dark",
                "before": "06:00",
                "after": "00:00",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.dark")
    assert state.state == STATE_ON
    assert state.attributes["after"] == "2019-01-11T00:00:00+01:00"
    assert state.attributes["before"] == "2019-01-11T06:00:00+01:00"
    assert state.attributes["next_update"] == "2019-01-11T06:00:00+01:00"


async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique id."""
    config = {
        "binary_sensor": [
            {
                "platform": "tod",
                "name": "Evening",
                "after": "18:00",
                "before": "22:00",
                "unique_id": "very_unique_id",
            }
        ]
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    entity = entity_registry.async_get("binary_sensor.evening")

    assert entity.unique_id == "very_unique_id"
