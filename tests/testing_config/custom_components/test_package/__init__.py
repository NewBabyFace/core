"""Provide a mock package component."""

from menuai.core import menuai
from menuai.helpers.typing import ConfigType

from .const import TEST  # noqa: F401

DOMAIN = "test_package"


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Mock a successful setup."""
    return True
