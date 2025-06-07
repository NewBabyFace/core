"""Sensors for National Weather Service (NWS)."""

import pytest

from menuai.components.nws.const import ATTRIBUTION, DOMAIN
from menuai.components.nws.sensor import SENSOR_TYPES
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.const import ATTR_ATTRIBUTION, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import slugify
from menuai.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

from .const import (
    EXPECTED_FORECAST_IMPERIAL,
    EXPECTED_FORECAST_METRIC,
    NONE_OBSERVATION,
    NWS_CONFIG,
    SENSOR_EXPECTED_OBSERVATION_IMPERIAL,
    SENSOR_EXPECTED_OBSERVATION_METRIC,
)

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("units", "result_observation", "result_forecast"),
    [
        (
            US_CUSTOMARY_SYSTEM,
            SENSOR_EXPECTED_OBSERVATION_IMPERIAL,
            EXPECTED_FORECAST_IMPERIAL,
        ),
        (METRIC_SYSTEM, SENSOR_EXPECTED_OBSERVATION_METRIC, EXPECTED_FORECAST_METRIC),
    ],
)
async def test_imperial_metric(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    units,
    result_observation,
    result_forecast,
    mock_simple_nws,
    no_weather,
) -> None:
    """Test with imperial and metric units."""
    for description in SENSOR_TYPES:
        entity_registry.async_get_or_create(
            SENSOR_DOMAIN,
            DOMAIN,
            f"35_-75_{description.key}",
            suggested_object_id=f"abc_{description.name}",
            disabled_by=None,
        )

    menuai.config.units = units
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=NWS_CONFIG,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    for description in SENSOR_TYPES:
        assert description.name
        state = menuai.states.get(f"sensor.abc_{slugify(description.name)}")
        assert state
        assert state.state == result_observation[description.key], (
            f"Failed for {description.key}"
        )
        assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION


@pytest.mark.parametrize("values", [NONE_OBSERVATION, None])
async def test_none_values(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_simple_nws,
    no_weather,
    values,
) -> None:
    """Test with no values."""
    instance = mock_simple_nws.return_value
    instance.observation = values

    for description in SENSOR_TYPES:
        entity_registry.async_get_or_create(
            SENSOR_DOMAIN,
            DOMAIN,
            f"35_-75_{description.key}",
            suggested_object_id=f"abc_{description.name}",
            disabled_by=None,
        )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=NWS_CONFIG,
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    for description in SENSOR_TYPES:
        assert description.name
        state = menuai.states.get(f"sensor.abc_{slugify(description.name)}")
        assert state
        assert state.state == STATE_UNKNOWN
