"""Send instance and usage analytics."""

from typing import Any

import voluptuous as vol

from menuai.components import websocket_api
from menuai.const import EVENT_menuai_STARTED
from menuai.core import Event, menuaiJob, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.event import async_call_later, async_track_time_interval
from menuai.helpers.typing import ConfigType
from menuai.util.menuai_dict import menuaiKey

from .analytics import Analytics
from .const import ATTR_ONBOARDED, ATTR_PREFERENCES, DOMAIN, INTERVAL, PREFERENCE_SCHEMA

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

DATA_COMPONENT: menuaiKey[Analytics] = menuaiKey(DOMAIN)


async def async_setup(menuai: menuai, _: ConfigType) -> bool:
    """Set up the analytics integration."""
    analytics = Analytics(menuai)

    # Load stored data
    await analytics.load()

    @callback
    def start_schedule(_event: Event) -> None:
        """Start the send schedule after the started event."""
        # Wait 15 min after started
        async_call_later(
            menuai,
            900,
            menuaiJob(
                analytics.send_analytics,
                name="analytics schedule",
                cancel_on_shutdown=True,
            ),
        )

        # Send every day
        async_track_time_interval(
            menuai,
            analytics.send_analytics,
            INTERVAL,
            name="analytics daily",
            cancel_on_shutdown=True,
        )

    menuai.bus.async_listen_once(EVENT_menuai_STARTED, start_schedule)

    websocket_api.async_register_command(menuai, websocket_analytics)
    websocket_api.async_register_command(menuai, websocket_analytics_preferences)

    menuai.data[DATA_COMPONENT] = analytics
    return True


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "analytics"})
def websocket_analytics(
    menuai: menuai,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return analytics preferences."""
    analytics = menuai.data[DATA_COMPONENT]
    connection.send_result(
        msg["id"],
        {ATTR_PREFERENCES: analytics.preferences, ATTR_ONBOARDED: analytics.onboarded},
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "analytics/preferences",
        vol.Required("preferences", default={}): PREFERENCE_SCHEMA,
    }
)
@websocket_api.async_response
async def websocket_analytics_preferences(
    menuai: menuai,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update analytics preferences."""
    preferences = msg[ATTR_PREFERENCES]
    analytics = menuai.data[DATA_COMPONENT]

    await analytics.save_preferences(preferences)
    await analytics.send_analytics()

    connection.send_result(
        msg["id"],
        {ATTR_PREFERENCES: analytics.preferences},
    )
