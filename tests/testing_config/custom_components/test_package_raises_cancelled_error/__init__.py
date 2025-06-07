"""Provide a mock package component."""

import asyncio

from menuai.core import menuai
from menuai.helpers.typing import ConfigType


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Mock a successful setup."""
    asyncio.current_task().cancel()
    await asyncio.sleep(0)
