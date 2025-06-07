"""Test the Qingping binary sensors."""

from datetime import timedelta
import time

from menuai.components.bluetooth import (
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
)
from menuai.components.qingping.const import DOMAIN
from menuai.const import ATTR_FRIENDLY_NAME, STATE_OFF, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import LIGHT_AND_SIGNAL_SERVICE_INFO, NO_DATA_SERVICE_INFO

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
    patch_bluetooth_time,
)


async def test_binary_sensors(menuai: menuai) -> None:
    """Test setting up creates the binary sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("binary_sensor")) == 0
    inject_bluetooth_service_info(menuai, LIGHT_AND_SIGNAL_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("binary_sensor")) == 1

    motion_sensor = menuai.states.get("binary_sensor.motion_light_eeff_motion")
    assert motion_sensor.state == "off"
    assert motion_sensor.attributes[ATTR_FRIENDLY_NAME] == "Motion & Light EEFF Motion"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_binary_sensor_restore_state(menuai: menuai) -> None:
    """Test setting up creates the binary sensors and restoring state."""
    start_monotonic = time.monotonic()

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("binary_sensor")) == 0
    inject_bluetooth_service_info(menuai, LIGHT_AND_SIGNAL_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("binary_sensor")) == 1

    motion_sensor = menuai.states.get("binary_sensor.motion_light_eeff_motion")
    assert motion_sensor.state == STATE_OFF
    assert motion_sensor.attributes[ATTR_FRIENDLY_NAME] == "Motion & Light EEFF Motion"

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

    # Device is no longer available because its not in range

    motion_sensor = menuai.states.get("binary_sensor.motion_light_eeff_motion")
    assert motion_sensor.state == STATE_UNAVAILABLE

    # Device is back in range

    inject_bluetooth_service_info(menuai, NO_DATA_SERVICE_INFO)

    motion_sensor = menuai.states.get("binary_sensor.motion_light_eeff_motion")
    assert motion_sensor.state == STATE_OFF
