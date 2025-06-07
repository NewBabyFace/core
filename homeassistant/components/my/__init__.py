"""Support for my.home-assistant.io redirect service."""

from menuai.components import frontend
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

DOMAIN = "my"
URL_PATH = "_my_redirect"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Register hidden _my_redirect panel."""
    frontend.async_register_built_in_panel(menuai, DOMAIN, frontend_url_path=URL_PATH)
    return True
