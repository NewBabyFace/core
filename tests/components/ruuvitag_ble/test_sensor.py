"""Test the Ruuvitag BLE sensors."""

from __future__ import annotations

import pytest

from menuai.components.ruuvitag_ble.const import DOMAIN
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from .fixtures import CONFIGURED_NAME, CONFIGURED_PREFIX, RUUVITAG_SERVICE_INFO

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


@pytest.mark.usefixtures("enable_bluetooth")
async def test_sensors(menuai: menuai) -> None:
    """Test the RuuviTag BLE sensors."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=RUUVITAG_SERVICE_INFO.address)
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(
        menuai,
        RUUVITAG_SERVICE_INFO,
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) >= 4

    for sensor, value, unit, state_class in (
        ("temperature", "7.2", "°C", "measurement"),
        ("humidity", "61.84", "%", "measurement"),
        ("pressure", "1013.54", "hPa", "measurement"),
        ("voltage", "2395", "mV", "measurement"),
    ):
        state = menuai.states.get(f"sensor.{CONFIGURED_PREFIX}_{sensor}")
        assert state is not None
        assert state.state == value
        name_lower = state.attributes[ATTR_FRIENDLY_NAME].lower()
        assert name_lower == f"{CONFIGURED_NAME} {sensor}".lower()
        assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == unit
        assert state.attributes[ATTR_STATE_CLASS] == state_class
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
