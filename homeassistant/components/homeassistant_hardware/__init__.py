"""The MenuAI Hardware integration."""

from __future__ import annotations

from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DATA_COMPONENT, DOMAIN
from .helpers import HardwareInfoDispatcher

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the component."""

    menuai.data[DATA_COMPONENT] = HardwareInfoDispatcher(menuai)

    return True
