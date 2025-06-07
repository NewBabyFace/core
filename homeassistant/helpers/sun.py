"""Helpers for sun events."""

from __future__ import annotations

from collections.abc import Callable
import datetime
from typing import TYPE_CHECKING, Any, cast

from menuai.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from menuai.core import menuai, callback
from menuai.loader import bind_menuai
from menuai.util import dt as dt_util
from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    import astral
    import astral.location

DATA_LOCATION_CACHE: menuaiKey[
    dict[tuple[str, str, str, float, float], astral.location.Location]
] = menuaiKey("astral_location_cache")

ELEVATION_AGNOSTIC_EVENTS = ("noon", "midnight")

type _AstralSunEventCallable = Callable[..., datetime.datetime]


@callback
@bind_menuai
def get_astral_location(
    menuai: menuai,
) -> tuple[astral.location.Location, astral.Elevation]:
    """Get an astral location for the current MenuAI configuration."""
    from astral import LocationInfo  # pylint: disable=import-outside-toplevel
    from astral.location import Location  # pylint: disable=import-outside-toplevel

    latitude = menuai.config.latitude
    longitude = menuai.config.longitude
    timezone = str(menuai.config.time_zone)
    elevation = menuai.config.elevation
    info = ("", "", timezone, latitude, longitude)

    # Cache astral locations so they aren't recreated with the same args
    if DATA_LOCATION_CACHE not in menuai.data:
        menuai.data[DATA_LOCATION_CACHE] = {}

    if info not in menuai.data[DATA_LOCATION_CACHE]:
        menuai.data[DATA_LOCATION_CACHE][info] = Location(LocationInfo(*info))

    return menuai.data[DATA_LOCATION_CACHE][info], elevation


@callback
@bind_menuai
def get_astral_event_next(
    menuai: menuai,
    event: str,
    utc_point_in_time: datetime.datetime | None = None,
    offset: datetime.timedelta | None = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""
    location, elevation = get_astral_location(menuai)
    return get_location_astral_event_next(
        location, elevation, event, utc_point_in_time, offset
    )


@callback
def get_location_astral_event_next(
    location: astral.location.Location,
    elevation: astral.Elevation,
    event: str,
    utc_point_in_time: datetime.datetime | None = None,
    offset: datetime.timedelta | None = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""

    if offset is None:
        offset = datetime.timedelta()

    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    kwargs: dict[str, Any] = {"local": False}
    if event not in ELEVATION_AGNOSTIC_EVENTS:
        kwargs["observer_elevation"] = elevation

    mod = -1
    first_err = None
    while mod < 367:
        try:
            next_dt = (
                cast(_AstralSunEventCallable, getattr(location, event))(
                    dt_util.as_local(utc_point_in_time).date()
                    + datetime.timedelta(days=mod),
                    **kwargs,
                )
                + offset
            )
            if next_dt > utc_point_in_time:
                return next_dt
        except ValueError as err:
            if not first_err:
                first_err = err
        mod += 1
    raise ValueError(
        f"Unable to find event after one year, initial ValueError: {first_err}"
    ) from first_err


@callback
@bind_menuai
def get_astral_event_date(
    menuai: menuai,
    event: str,
    date: datetime.date | datetime.datetime | None = None,
) -> datetime.datetime | None:
    """Calculate the astral event time for the specified date."""
    location, elevation = get_astral_location(menuai)

    if date is None:
        date = dt_util.now().date()

    if isinstance(date, datetime.datetime):
        date = dt_util.as_local(date).date()

    kwargs: dict[str, Any] = {"local": False}
    if event not in ELEVATION_AGNOSTIC_EVENTS:
        kwargs["observer_elevation"] = elevation

    try:
        return cast(_AstralSunEventCallable, getattr(location, event))(date, **kwargs)
    except ValueError:
        # Event never occurs for specified date.
        return None


@callback
@bind_menuai
def is_up(
    menuai: menuai, utc_point_in_time: datetime.datetime | None = None
) -> bool:
    """Calculate if the sun is currently up."""
    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    next_sunrise = get_astral_event_next(menuai, SUN_EVENT_SUNRISE, utc_point_in_time)
    next_sunset = get_astral_event_next(menuai, SUN_EVENT_SUNSET, utc_point_in_time)

    return next_sunrise > next_sunset
