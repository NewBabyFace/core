"""Test the Melnor time platform."""

from __future__ import annotations

from datetime import time, timedelta

from menuai.core import menuai
from menuai.util import dt as dt_util

from .conftest import (
    mock_config_entry,
    patch_async_ble_device_from_address,
    patch_async_register_callback,
    patch_melnor_device,
)

from tests.common import async_fire_time_changed


async def test_schedule_start_time(menuai: menuai) -> None:
    """Test the frequency schedule start time."""

    now = dt_util.now()

    entry = mock_config_entry(menuai)

    with (
        patch_async_ble_device_from_address(),
        patch_melnor_device() as device_patch,
        patch_async_register_callback(),
    ):
        device = device_patch.return_value

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        time_entity = menuai.states.get("time.zone_1_schedule_start_time")

        assert time_entity is not None
        assert time_entity.state == device.zone1.frequency.start_time.isoformat()

        await menuai.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.zone_1_schedule_start_time", "time": time(1, 0)},
            blocking=True,
        )

        async_fire_time_changed(menuai, now + timedelta(seconds=10))
        await menuai.async_block_till_done()

        time_entity = menuai.states.get("time.zone_1_schedule_start_time")

        assert time_entity is not None
        assert time_entity.state == time(1, 0).isoformat()
