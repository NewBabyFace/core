"""Component providing default configuration for new users."""

from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

DOMAIN = "default_config"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Initialize default configuration."""
    return True
