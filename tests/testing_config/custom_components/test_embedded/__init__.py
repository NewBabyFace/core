"""Component with embedded platforms."""

from menuai.core import menuai
from menuai.helpers.typing import ConfigType

DOMAIN = "test_embedded"


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Mock config."""
    return True
