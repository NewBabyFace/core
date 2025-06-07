"""Provide a mock standalone component."""

from menuai.core import menuai
from menuai.helpers.typing import ConfigType

DOMAIN = "test_standalone"


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Mock a successful setup."""
    return True
