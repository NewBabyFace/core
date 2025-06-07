"""Provide a mock package component."""

import asyncio

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.typing import ConfigType


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Mock a successful setup."""
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Mock an unsuccessful entry setup."""
    asyncio.current_task().cancel()
    await asyncio.sleep(0)
