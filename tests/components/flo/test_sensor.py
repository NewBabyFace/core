"""Test Flo by Moen sensor entities."""

import pytest

from menuai.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_sensors(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test Flo by Moen sensors."""
    menuai.config.units = US_CUSTOMARY_SYSTEM
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # we should have 5 entities for the valve
    assert (
        menuai.states.get("sensor.smart_water_shutoff_current_system_mode").state
        == "home"
    )

    assert (
        menuai.states.get("sensor.smart_water_shutoff_today_s_water_usage").state == "3.7"
    )
    assert (
        menuai.states.get("sensor.smart_water_shutoff_today_s_water_usage").attributes[
            ATTR_STATE_CLASS
        ]
        == SensorStateClass.TOTAL_INCREASING
    )

    assert menuai.states.get("sensor.smart_water_shutoff_water_flow_rate").state == "0"
    assert (
        menuai.states.get("sensor.smart_water_shutoff_water_flow_rate").attributes[
            ATTR_STATE_CLASS
        ]
        == SensorStateClass.MEASUREMENT
    )

    assert menuai.states.get("sensor.smart_water_shutoff_water_pressure").state == "54.2"
    assert (
        menuai.states.get("sensor.smart_water_shutoff_water_pressure").attributes[
            ATTR_STATE_CLASS
        ]
        == SensorStateClass.MEASUREMENT
    )

    assert menuai.states.get("sensor.smart_water_shutoff_water_temperature").state == "70"
    assert (
        menuai.states.get("sensor.smart_water_shutoff_water_temperature").attributes[
            ATTR_STATE_CLASS
        ]
        == SensorStateClass.MEASUREMENT
    )

    # and 3 entities for the detector
    assert menuai.states.get("sensor.kitchen_sink_temperature").state == "61"
    assert (
        menuai.states.get("sensor.kitchen_sink_temperature").attributes[ATTR_STATE_CLASS]
        == SensorStateClass.MEASUREMENT
    )

    assert menuai.states.get("sensor.kitchen_sink_humidity").state == "43"
    assert (
        menuai.states.get("sensor.kitchen_sink_humidity").attributes[ATTR_STATE_CLASS]
        == SensorStateClass.MEASUREMENT
    )

    assert menuai.states.get("sensor.kitchen_sink_battery").state == "100"
    assert (
        menuai.states.get("sensor.kitchen_sink_battery").attributes[ATTR_STATE_CLASS]
        == SensorStateClass.MEASUREMENT
    )


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_manual_update_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test manual update entity via service homeasasistant/update_entity."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await async_setup_component(menuai, "menuai", {})

    call_count = aioclient_mock.call_count
    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {ATTR_ENTITY_ID: ["sensor.smart_water_shutoff_current_system_mode"]},
        blocking=True,
    )
    assert aioclient_mock.call_count == call_count + 3
