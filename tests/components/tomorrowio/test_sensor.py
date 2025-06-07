"""Tests for Tomorrow.io sensor entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from freezegun import freeze_time
import pytest

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN, async_rounded_state
from menuai.components.tomorrowio.config_flow import (
    _get_config_schema,
    _get_unique_id,
)
from menuai.components.tomorrowio.const import (
    ATTRIBUTION,
    CONF_TIMESTEP,
    DEFAULT_NAME,
    DEFAULT_TIMESTEP,
    DOMAIN,
)
from menuai.components.tomorrowio.sensor import TomorrowioSensorEntityDescription
from menuai.config_entries import RELOAD_AFTER_UPDATE_DELAY, SOURCE_USER
from menuai.const import ATTR_ATTRIBUTION, CONF_NAME
from menuai.core import menuai, State, callback
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from .const import API_V4_ENTRY_DATA

from tests.common import MockConfigEntry, async_fire_time_changed

CC_SENSOR_ENTITY_ID = "sensor.tomorrow_io_{}"

O3 = "ozone"
CO = "carbon_monoxide"
NO2 = "nitrogen_dioxide"
SO2 = "sulphur_dioxide"
PM25 = "pm2_5"
PM10 = "pm10"
MEP_AQI = "china_mep_air_quality_index"
MEP_HEALTH_CONCERN = "china_mep_health_concern"
MEP_PRIMARY_POLLUTANT = "china_mep_primary_pollutant"
EPA_AQI = "us_epa_air_quality_index"
EPA_HEALTH_CONCERN = "us_epa_health_concern"
EPA_PRIMARY_POLLUTANT = "us_epa_primary_pollutant"
FIRE_INDEX = "fire_index"
GRASS_POLLEN = "grass_pollen_index"
WEED_POLLEN = "weed_pollen_index"
TREE_POLLEN = "tree_pollen_index"
FEELS_LIKE = "feels_like"
DEW_POINT = "dew_point"
PRESSURE_SURFACE_LEVEL = "pressure"
SNOW_ACCUMULATION = "snow_accumulation"
ICE_ACCUMULATION = "ice_accumulation"
GHI = "irradiance"
CLOUD_BASE = "cloud_base"
CLOUD_COVER = "cloud_cover"
CLOUD_CEILING = "cloud_ceiling"
WIND_GUST = "wind_gust"
PRECIPITATION_TYPE = "precipitation_type"
UV_INDEX = "uv_index"
UV_HEALTH_CONCERN = "uv_radiation_health_concern"


V3_FIELDS = [
    O3,
    CO,
    NO2,
    SO2,
    PM25,
    PM10,
    MEP_AQI,
    MEP_HEALTH_CONCERN,
    MEP_PRIMARY_POLLUTANT,
    EPA_AQI,
    EPA_HEALTH_CONCERN,
    EPA_PRIMARY_POLLUTANT,
    FIRE_INDEX,
    GRASS_POLLEN,
    WEED_POLLEN,
    TREE_POLLEN,
]

V4_FIELDS = [
    *V3_FIELDS,
    FEELS_LIKE,
    DEW_POINT,
    PRESSURE_SURFACE_LEVEL,
    GHI,
    CLOUD_BASE,
    CLOUD_COVER,
    CLOUD_CEILING,
    WIND_GUST,
    PRECIPITATION_TYPE,
    UV_INDEX,
    UV_HEALTH_CONCERN,
]


@callback
def _enable_entity(menuai: menuai, entity_name: str) -> None:
    """Enable disabled entity."""
    ent_reg = er.async_get(menuai)
    entry = ent_reg.async_get(entity_name)
    updated_entry = ent_reg.async_update_entity(entry.entity_id, disabled_by=None)
    assert updated_entry != entry
    assert updated_entry.disabled is False


async def _setup(
    menuai: menuai, sensors: list[str], config: dict[str, Any]
) -> State:
    """Set up entry and return entity state."""
    with freeze_time(
        datetime(2021, 3, 6, 23, 59, 59, tzinfo=dt_util.UTC)
    ) as frozen_time:
        data = _get_config_schema(menuai, SOURCE_USER)(config)
        data[CONF_NAME] = DEFAULT_NAME
        config_entry = MockConfigEntry(
            title=DEFAULT_NAME,
            domain=DOMAIN,
            data=data,
            options={CONF_TIMESTEP: DEFAULT_TIMESTEP},
            unique_id=_get_unique_id(menuai, data),
            version=1,
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        for entity_name in sensors:
            _enable_entity(menuai, CC_SENSOR_ENTITY_ID.format(entity_name))
        await menuai.async_block_till_done()
        # the enabled entity state will be fired in RELOAD_AFTER_UPDATE_DELAY
        frozen_time.tick(delta=RELOAD_AFTER_UPDATE_DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert len(menuai.states.async_entity_ids(SENSOR_DOMAIN)) == len(sensors)


def check_sensor_state(menuai: menuai, entity_name: str, value: str):
    """Check the state of a Tomorrow.io sensor."""
    entity_id = CC_SENSOR_ENTITY_ID.format(entity_name)
    state = menuai.states.get(entity_id)
    assert state
    assert async_rounded_state(menuai, entity_id, state) == value
    assert state.attributes[ATTR_ATTRIBUTION] == ATTRIBUTION


async def test_v4_sensor(menuai: menuai) -> None:
    """Test v4 sensor data."""
    await _setup(menuai, V4_FIELDS, API_V4_ENTRY_DATA)
    check_sensor_state(menuai, O3, "91.35")
    check_sensor_state(menuai, CO, "0.0")
    check_sensor_state(menuai, NO2, "20.08")
    check_sensor_state(menuai, SO2, "4.32")
    check_sensor_state(menuai, PM25, "0.15")
    check_sensor_state(menuai, PM10, "0.57")
    check_sensor_state(menuai, MEP_AQI, "23")
    check_sensor_state(menuai, MEP_HEALTH_CONCERN, "good")
    check_sensor_state(menuai, MEP_PRIMARY_POLLUTANT, "pm10")
    check_sensor_state(menuai, EPA_AQI, "24")
    check_sensor_state(menuai, EPA_HEALTH_CONCERN, "good")
    check_sensor_state(menuai, EPA_PRIMARY_POLLUTANT, "pm25")
    check_sensor_state(menuai, FIRE_INDEX, "10")
    check_sensor_state(menuai, GRASS_POLLEN, "none")
    check_sensor_state(menuai, WEED_POLLEN, "none")
    check_sensor_state(menuai, TREE_POLLEN, "none")
    check_sensor_state(menuai, FEELS_LIKE, "101.3")
    check_sensor_state(menuai, DEW_POINT, "72.8")
    check_sensor_state(menuai, PRESSURE_SURFACE_LEVEL, "29.47")
    check_sensor_state(menuai, GHI, "0")
    check_sensor_state(menuai, CLOUD_BASE, "0.74")
    check_sensor_state(menuai, CLOUD_COVER, "100")
    check_sensor_state(menuai, CLOUD_CEILING, "0.74")
    check_sensor_state(menuai, WIND_GUST, "12.64")
    check_sensor_state(menuai, PRECIPITATION_TYPE, "rain")
    check_sensor_state(menuai, UV_INDEX, "3")
    check_sensor_state(menuai, UV_HEALTH_CONCERN, "moderate")


async def test_v4_sensor_imperial(menuai: menuai) -> None:
    """Test v4 sensor data."""
    menuai.config.units = US_CUSTOMARY_SYSTEM
    await _setup(menuai, V4_FIELDS, API_V4_ENTRY_DATA)
    check_sensor_state(menuai, O3, "91.35")
    check_sensor_state(menuai, CO, "0.0")
    check_sensor_state(menuai, NO2, "20.08")
    check_sensor_state(menuai, SO2, "4.32")
    check_sensor_state(menuai, PM25, "0.15")
    check_sensor_state(menuai, PM10, "0.57")
    check_sensor_state(menuai, MEP_AQI, "23")
    check_sensor_state(menuai, MEP_HEALTH_CONCERN, "good")
    check_sensor_state(menuai, MEP_PRIMARY_POLLUTANT, "pm10")
    check_sensor_state(menuai, EPA_AQI, "24")
    check_sensor_state(menuai, EPA_HEALTH_CONCERN, "good")
    check_sensor_state(menuai, EPA_PRIMARY_POLLUTANT, "pm25")
    check_sensor_state(menuai, FIRE_INDEX, "10")
    check_sensor_state(menuai, GRASS_POLLEN, "none")
    check_sensor_state(menuai, WEED_POLLEN, "none")
    check_sensor_state(menuai, TREE_POLLEN, "none")
    check_sensor_state(menuai, FEELS_LIKE, "214.3")
    check_sensor_state(menuai, DEW_POINT, "163.1")
    check_sensor_state(menuai, PRESSURE_SURFACE_LEVEL, "0.43")
    check_sensor_state(menuai, GHI, "0.0")
    check_sensor_state(menuai, CLOUD_BASE, "0.46")
    check_sensor_state(menuai, CLOUD_COVER, "100")
    check_sensor_state(menuai, CLOUD_CEILING, "0.46")
    check_sensor_state(menuai, WIND_GUST, "28.27")
    check_sensor_state(menuai, PRECIPITATION_TYPE, "rain")
    check_sensor_state(menuai, UV_INDEX, "3")
    check_sensor_state(menuai, UV_HEALTH_CONCERN, "moderate")


async def test_entity_description() -> None:
    """Test improper entity description raises."""
    with pytest.raises(ValueError):
        TomorrowioSensorEntityDescription("a", unit_imperial="b")
