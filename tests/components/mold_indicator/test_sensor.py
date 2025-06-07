"""The tests for the MoldIndicator sensor."""

import pytest

from menuai.components import sensor
from menuai.components.mold_indicator.sensor import (
    ATTR_CRITICAL_TEMP,
    ATTR_DEWPOINT,
)
from menuai.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def init_sensors_fixture(menuai: menuai) -> None:
    """Set up things to be run when tests are started."""
    menuai.states.async_set(
        "test.indoortemp", "20", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.outdoortemp", "10", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.indoorhumidity", "50", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )


async def test_setup(menuai: menuai) -> None:
    """Test the mold indicator sensor setup."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 2.0,
            }
        },
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.attributes.get("unit_of_measurement") == PERCENTAGE


async def test_setup_from_config_entry(
    menuai: menuai, loaded_entry: MockConfigEntry
) -> None:
    """Test the mold indicator sensor setup from a config entry."""

    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.attributes.get("unit_of_measurement") == PERCENTAGE


async def test_invalidcalib(menuai: menuai) -> None:
    """Test invalid sensor values."""
    menuai.states.async_set(
        "test.indoortemp", "10", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.outdoortemp", "10", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.indoorhumidity", "0", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )

    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 0,
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None


async def test_invalidhum(menuai: menuai) -> None:
    """Test invalid sensor values."""
    menuai.states.async_set(
        "test.indoortemp", "10", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.outdoortemp", "10", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.indoorhumidity", "-1", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )

    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 2.0,
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None

    menuai.states.async_set(
        "test.indoorhumidity", "A", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None

    menuai.states.async_set(
        "test.indoorhumidity",
        "10",
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None


async def test_calculation(menuai: menuai) -> None:
    """Test the mold indicator internal calculations."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 2.0,
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind

    # assert dewpoint
    dewpoint = moldind.attributes.get(ATTR_DEWPOINT)
    assert dewpoint
    assert dewpoint > 9.2
    assert dewpoint < 9.3

    # assert temperature estimation
    esttemp = moldind.attributes.get(ATTR_CRITICAL_TEMP)
    assert esttemp
    assert esttemp > 14.9
    assert esttemp < 15.1

    # assert mold indicator value
    state = moldind.state
    assert state
    assert state == "68"


async def test_unknown_sensor(menuai: menuai) -> None:
    """Test the sensor_changed function."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 2.0,
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()

    menuai.states.async_set(
        "test.indoortemp",
        STATE_UNKNOWN,
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None

    menuai.states.async_set(
        "test.indoortemp", "30", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.outdoortemp",
        STATE_UNKNOWN,
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None

    menuai.states.async_set(
        "test.outdoortemp", "25", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    menuai.states.async_set(
        "test.indoorhumidity",
        STATE_UNKNOWN,
        {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE},
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "unavailable"
    assert moldind.attributes.get(ATTR_DEWPOINT) is None
    assert moldind.attributes.get(ATTR_CRITICAL_TEMP) is None

    menuai.states.async_set(
        "test.indoorhumidity", "20", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await menuai.async_block_till_done()
    moldind = menuai.states.get("sensor.mold_indicator")
    assert moldind
    assert moldind.state == "23"

    dewpoint = moldind.attributes.get(ATTR_DEWPOINT)
    assert dewpoint
    assert dewpoint > 4.5
    assert dewpoint < 4.6

    esttemp = moldind.attributes.get(ATTR_CRITICAL_TEMP)
    assert esttemp
    assert esttemp == 27.5


async def test_sensor_changed(menuai: menuai) -> None:
    """Test the sensor_changed function."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            "sensor": {
                "platform": "mold_indicator",
                "indoor_temp_sensor": "test.indoortemp",
                "outdoor_temp_sensor": "test.outdoortemp",
                "indoor_humidity_sensor": "test.indoorhumidity",
                "calibration_factor": 2.0,
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()

    menuai.states.async_set(
        "test.indoortemp", "30", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.mold_indicator").state == "90"

    menuai.states.async_set(
        "test.outdoortemp", "25", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.mold_indicator").state == "57"

    menuai.states.async_set(
        "test.indoorhumidity", "20", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.mold_indicator").state == "23"
