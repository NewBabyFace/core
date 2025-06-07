"""Offer sun based automation rules."""

from datetime import timedelta

import voluptuous as vol

from menuai.const import (
    CONF_EVENT,
    CONF_OFFSET,
    CONF_PLATFORM,
    SUN_EVENT_SUNRISE,
)
from menuai.core import CALLBACK_TYPE, menuaiJob, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.event import async_track_sunrise, async_track_sunset
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

TRIGGER_SCHEMA = cv.TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): "sun",
        vol.Required(CONF_EVENT): cv.sun_event,
        vol.Required(CONF_OFFSET, default=timedelta(0)): cv.time_period,
    }
)


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for events based on configuration."""
    trigger_data = trigger_info["trigger_data"]
    event = config.get(CONF_EVENT)
    offset = config.get(CONF_OFFSET)
    description = event
    if offset:
        description = f"{description} with offset"
    job = menuaiJob(action)

    @callback
    def call_action() -> None:
        """Call action with right context."""
        menuai.async_run_menuai_job(
            job,
            {
                "trigger": {
                    **trigger_data,
                    "platform": "sun",
                    "event": event,
                    "offset": offset,
                    "description": description,
                }
            },
        )

    if event == SUN_EVENT_SUNRISE:
        return async_track_sunrise(menuai, call_action, offset)
    return async_track_sunset(menuai, call_action, offset)
