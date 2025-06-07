"""Support for Lupusec Home Security system."""

from json import JSONDecodeError
import logging

import lupupy
from lupupy.exceptions import LupusecException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai

_LOGGER = logging.getLogger(__name__)

DOMAIN = "lupusec"

NOTIFICATION_ID = "lupusec_notification"
NOTIFICATION_TITLE = "Lupusec Security Setup"


PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        lupusec_system = await menuai.async_add_executor_job(
            lupupy.Lupusec, username, password, host
        )
    except LupusecException:
        _LOGGER.error("Failed to connect to Lupusec device at %s", host)
        return False
    except JSONDecodeError:
        _LOGGER.error("Failed to connect to Lupusec device at %s", host)
        return False

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = lupusec_system

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
