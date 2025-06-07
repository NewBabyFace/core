"""Tests for the smarttub integration."""

from datetime import timedelta

from menuai.components.smarttub.const import SCAN_INTERVAL
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed


async def trigger_update(menuai: menuai) -> None:
    """Trigger a polling update by moving time forward."""
    new_time = dt_util.utcnow() + timedelta(seconds=SCAN_INTERVAL + 1)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done(wait_background_tasks=True)
