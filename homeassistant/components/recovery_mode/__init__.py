"""The Recovery Mode integration."""

from menuai.components import persistent_notification
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

DOMAIN = "recovery_mode"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Recovery Mode component."""
    persistent_notification.async_create(
        menuai,
        (
            "MenuAI is running in recovery mode. Check [the error"
            " log](/config/logs) to see what went wrong."
        ),
        "Recovery Mode",
    )
    return True
