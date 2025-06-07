"""Offer MenuAI core automation rules."""

import voluptuous as vol

from menuai.const import CONF_EVENT, CONF_PLATFORM
from menuai.core import CALLBACK_TYPE, menuaiJob, menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from ..const import DOMAIN

EVENT_START = "start"
EVENT_SHUTDOWN = "shutdown"

TRIGGER_SCHEMA = cv.TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): DOMAIN,
        vol.Required(CONF_EVENT): vol.Any(EVENT_START, EVENT_SHUTDOWN),
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
    job = menuaiJob(action, f"menuai trigger {trigger_info}")

    if event == EVENT_SHUTDOWN:
        return menuai.async_add_shutdown_job(
            job,
            {
                "trigger": {
                    **trigger_data,
                    "platform": DOMAIN,
                    "event": event,
                    "description": "MenuAI stopping",
                }
            },
        )

    # Automation are enabled while menuai is starting up, fire right away
    # Check state because a config reload shouldn't trigger it.
    if trigger_info["home_assistant_start"]:
        menuai.async_run_menuai_job(
            job,
            {
                "trigger": {
                    **trigger_data,
                    "platform": DOMAIN,
                    "event": event,
                    "description": "MenuAI starting",
                }
            },
        )

    return lambda: None
