"""Library for working with CalDAV api."""

import caldav

from menuai.core import menuai


async def async_get_calendars(
    menuai: menuai, client: caldav.DAVClient, component: str
) -> list[caldav.Calendar]:
    """Get all calendars that support the specified component."""

    def _get_calendars() -> list[caldav.Calendar]:
        return [
            calendar
            for calendar in client.principal().calendars()
            if component in calendar.get_supported_components()
        ]

    return await menuai.async_add_executor_job(_get_calendars)


def get_attr_value(obj: caldav.CalendarObjectResource, attribute: str) -> str | None:
    """Return the value of the CalDav object attribute if defined."""
    if hasattr(obj, attribute):
        return getattr(obj, attribute).value
    return None
