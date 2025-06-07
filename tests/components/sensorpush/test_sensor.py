"""Test the SensorPush sensors."""

from datetime import timedelta
import time

from menuai.components.bluetooth import (
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
)
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.components.sensorpush.const import DOMAIN
from menuai.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import HTPWX_EMPTY_SERVICE_INFO, HTPWX_SERVICE_INFO

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
    patch_bluetooth_time,
)


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    start_monotonic = time.monotonic()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="4125DDBA-2774-4851-9889-6AADDD4CAC3D",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, HTPWX_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.htp_xw_f4d_temperature")
    temp_sensor_attributes = temp_sensor.attributes
    assert temp_sensor.state == "20.11"
    assert temp_sensor_attributes[ATTR_FRIENDLY_NAME] == "HTP.xw F4D Temperature"
    assert temp_sensor_attributes[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temp_sensor_attributes[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    # Fastforward time without BLE advertisements
    monotonic_now = start_monotonic + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1

    with (
        patch_bluetooth_time(
            monotonic_now,
        ),
        patch_all_discovered_devices([]),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow()
            + timedelta(seconds=FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1),
        )
        await menuai.async_block_till_done()

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    temp_sensor = menuai.states.get("sensor.htp_xw_f4d_temperature")
    assert temp_sensor.state == STATE_UNAVAILABLE
    inject_bluetooth_service_info(menuai, HTPWX_EMPTY_SERVICE_INFO)
    await menuai.async_block_till_done()

    temp_sensor = menuai.states.get("sensor.htp_xw_f4d_temperature")
    assert temp_sensor.state == "20.11"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
