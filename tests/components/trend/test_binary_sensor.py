"""The test for the Trend sensor platform."""

from datetime import timedelta
import logging
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import setup
from menuai.components.trend.const import DOMAIN
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai, State
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .conftest import ComponentSetup

from tests.common import MockConfigEntry, assert_setup_component, mock_restore_cache


async def _setup_legacy_component(menuai: menuai, params: dict[str, Any]) -> None:
    """Set up the trend component the legacy way."""
    assert await async_setup_component(
        menuai,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": "trend",
                "sensors": {
                    "test_trend_sensor": params,
                },
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    ("states", "inverted", "expected_state"),
    [
        (["1", "2"], False, STATE_ON),
        (["2", "1"], False, STATE_OFF),
        (["1", "2"], True, STATE_OFF),
        (["2", "1"], True, STATE_ON),
    ],
    ids=["up", "down", "up inverted", "down inverted"],
)
async def test_basic_trend_setup_from_yaml(
    menuai: menuai,
    states: list[str],
    inverted: bool,
    expected_state: str,
) -> None:
    """Test trend with a basic setup."""
    await _setup_legacy_component(
        menuai,
        {
            "friendly_name": "Test state",
            "entity_id": "sensor.cpu_temp",
            "invert": inverted,
            "max_samples": 2.0,
            "min_gradient": 0.0,
            "sample_duration": 0.0,
        },
    )

    for state in states:
        menuai.states.async_set("sensor.cpu_temp", state)
        await menuai.async_block_till_done()

    assert (sensor_state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert sensor_state.state == expected_state


@pytest.mark.parametrize(
    ("states", "inverted", "expected_state"),
    [
        (["1", "2"], False, STATE_ON),
        (["2", "1"], False, STATE_OFF),
        (["1", "2"], True, STATE_OFF),
        (["2", "1"], True, STATE_ON),
    ],
    ids=["up", "down", "up inverted", "down inverted"],
)
async def test_basic_trend(
    menuai: menuai,
    config_entry: MockConfigEntry,
    setup_component: ComponentSetup,
    states: list[str],
    inverted: bool,
    expected_state: str,
) -> None:
    """Test trend with a basic setup."""
    await setup_component(
        {
            "invert": inverted,
        },
    )

    for state in states:
        menuai.states.async_set("sensor.test_state", state)
        await menuai.async_block_till_done()

    assert (sensor_state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert sensor_state.state == expected_state


@pytest.mark.parametrize(
    ("state_series", "inverted", "expected_states"),
    [
        (
            [[10, 0, 20, 30], [100], [0, 30, 1, 0]],
            False,
            [STATE_UNKNOWN, STATE_ON, STATE_OFF],
        ),
        (
            [[10, 0, 20, 30], [100], [0, 30, 1, 0]],
            True,
            [STATE_UNKNOWN, STATE_OFF, STATE_ON],
        ),
        (
            [[30, 20, 30, 10], [5], [30, 0, 45, 60]],
            True,
            [STATE_UNKNOWN, STATE_ON, STATE_OFF],
        ),
    ],
    ids=["up", "up inverted", "down"],
)
async def test_using_trendline(
    menuai: menuai,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    setup_component: ComponentSetup,
    state_series: list[list[str]],
    inverted: bool,
    expected_states: list[str],
) -> None:
    """Test uptrend using multiple samples and trendline calculation."""
    await setup_component(
        {
            "sample_duration": 10000,
            "min_gradient": 1,
            "max_samples": 25,
            "min_samples": 5,
            "invert": inverted,
        },
    )

    for idx, states in enumerate(state_series):
        for state in states:
            freezer.tick(timedelta(seconds=2))
            menuai.states.async_set("sensor.test_state", state)
            await menuai.async_block_till_done()

        assert (sensor_state := menuai.states.get("binary_sensor.test_trend_sensor"))
        assert sensor_state.state == expected_states[idx]


@pytest.mark.parametrize(
    ("attr_values", "expected_state"),
    [
        (["1", "2"], STATE_ON),
        (["2", "1"], STATE_OFF),
    ],
    ids=["up", "down"],
)
async def test_attribute_trend(
    menuai: menuai,
    config_entry: MockConfigEntry,
    setup_component: ComponentSetup,
    attr_values: list[str],
    expected_state: str,
) -> None:
    """Test attribute uptrend."""
    await setup_component(
        {
            "entity_id": "sensor.test_state",
            "attribute": "attr",
        },
    )

    for attr in attr_values:
        menuai.states.async_set("sensor.test_state", "State", {"attr": attr})
        await menuai.async_block_till_done()

    assert (sensor_state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert sensor_state.state == expected_state


async def test_max_samples(
    menuai: menuai, config_entry: MockConfigEntry, setup_component: ComponentSetup
) -> None:
    """Test that sample count is limited correctly."""
    await setup_component(
        {
            "max_samples": 3,
            "min_gradient": -1,
        },
    )

    for val in (0, 1, 2, 3, 2, 1):
        menuai.states.async_set("sensor.test_state", val)
        await menuai.async_block_till_done()

    assert (state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert state.state == "on"
    assert state.attributes["sample_count"] == 3


async def test_non_numeric(
    menuai: menuai, config_entry: MockConfigEntry, setup_component: ComponentSetup
) -> None:
    """Test for non-numeric sensor."""
    await setup_component({"entity_id": "sensor.test_state"})

    for val in ("Non", "Numeric"):
        menuai.states.async_set("sensor.test_state", val)
        await menuai.async_block_till_done()

    assert (state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert state.state == STATE_UNKNOWN


async def test_missing_attribute(
    menuai: menuai, config_entry: MockConfigEntry, setup_component: ComponentSetup
) -> None:
    """Test for missing attribute."""
    await setup_component(
        {
            "attribute": "missing",
        },
    )

    for val in (1, 2):
        menuai.states.async_set("sensor.test_state", "State", {"attr": val})
        await menuai.async_block_till_done()

    assert (state := menuai.states.get("binary_sensor.test_trend_sensor"))
    assert state.state == STATE_UNKNOWN


async def test_invalid_name_does_not_create(menuai: menuai) -> None:
    """Test for invalid name."""
    with assert_setup_component(0):
        assert await setup.async_setup_component(
            menuai,
            "binary_sensor",
            {
                "binary_sensor": {
                    "platform": "trend",
                    "sensors": {
                        "test INVALID sensor": {"entity_id": "sensor.test_state"}
                    },
                }
            },
        )
    assert menuai.states.async_all("binary_sensor") == []


async def test_invalid_sensor_does_not_create(menuai: menuai) -> None:
    """Test invalid sensor."""
    with assert_setup_component(0):
        assert await setup.async_setup_component(
            menuai,
            "binary_sensor",
            {
                "binary_sensor": {
                    "platform": "trend",
                    "sensors": {
                        "test_trend_sensor": {"not_entity_id": "sensor.test_state"}
                    },
                }
            },
        )
    assert menuai.states.async_all("binary_sensor") == []


async def test_no_sensors_does_not_create(menuai: menuai) -> None:
    """Test no sensors."""
    with assert_setup_component(0):
        assert await setup.async_setup_component(
            menuai, "binary_sensor", {"binary_sensor": {"platform": "trend"}}
        )
    assert menuai.states.async_all("binary_sensor") == []


@pytest.mark.parametrize(
    ("saved_state", "restored_state"),
    [("on", "on"), ("off", "off"), ("unknown", "unknown")],
)
async def test_restore_state(
    menuai: menuai,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    setup_component: ComponentSetup,
    saved_state: str,
    restored_state: str,
) -> None:
    """Test we restore the trend state."""
    mock_restore_cache(menuai, (State("binary_sensor.test_trend_sensor", saved_state),))

    await setup_component(
        {
            "sample_duration": 10000,
            "min_gradient": 1,
            "max_samples": 25,
            "min_samples": 5,
        },
    )

    # restored sensor should match saved one
    assert menuai.states.get("binary_sensor.test_trend_sensor").state == restored_state

    # add not enough samples to trigger calculation
    for val in (10, 20, 30, 40):
        freezer.tick(timedelta(seconds=2))
        menuai.states.async_set("sensor.test_state", val)
        await menuai.async_block_till_done()

    # state should match restored state as no calculation happened
    assert menuai.states.get("binary_sensor.test_trend_sensor").state == restored_state

    # add more samples to trigger calculation
    for val in (50, 60, 70, 80):
        freezer.tick(timedelta(seconds=2))
        menuai.states.async_set("sensor.test_state", val)
        await menuai.async_block_till_done()

    # sensor should detect an upwards trend and turn on
    assert menuai.states.get("binary_sensor.test_trend_sensor").state == "on"


async def test_invalid_min_sample(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test if error is logged when min_sample is larger than max_samples."""
    with caplog.at_level(logging.ERROR):
        await _setup_legacy_component(
            menuai,
            {
                "entity_id": "sensor.test_state",
                "max_samples": 25,
                "min_samples": 30,
            },
        )

    record = caplog.records[0]
    assert record.levelname == "ERROR"
    assert (
        "Invalid config for 'binary_sensor' from integration 'trend': min_samples must "
        "be smaller than or equal to max_samples" in record.message
    )


async def test_device_id(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test for source entity device for Trend."""
    source_config_entry = MockConfigEntry()
    source_config_entry.add_to_menuai(menuai)
    source_device_entry = device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={("sensor", "identifier_test")},
        connections={("mac", "30:31:32:33:34:35")},
    )
    source_entity = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "source",
        config_entry=source_config_entry,
        device_id=source_device_entry.id,
    )
    await menuai.async_block_till_done()
    assert entity_registry.async_get("sensor.test_source") is not None

    trend_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "Trend",
            "entity_id": "sensor.test_source",
            "invert": False,
        },
        title="Trend",
    )
    trend_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(trend_config_entry.entry_id)
    await menuai.async_block_till_done()

    trend_entity = entity_registry.async_get("binary_sensor.trend")
    assert trend_entity is not None
    assert trend_entity.device_id == source_entity.device_id


@pytest.mark.parametrize(
    "error_state",
    [
        STATE_UNKNOWN,
        STATE_UNAVAILABLE,
    ],
)
async def test_unavailable_source(
    menuai: menuai,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    setup_component: ComponentSetup,
    error_state: str,
) -> None:
    """Test for unavailable source."""
    await setup_component(
        {
            "sample_duration": 10000,
            "min_gradient": 1,
            "max_samples": 25,
            "min_samples": 5,
        },
    )

    for val in (10, 20, 30, 40, 50, 60):
        freezer.tick(timedelta(seconds=2))
        menuai.states.async_set("sensor.test_state", val)
        await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_trend_sensor").state == "on"

    menuai.states.async_set("sensor.test_state", error_state)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_trend_sensor").state == STATE_UNAVAILABLE

    menuai.states.async_set("sensor.test_state", 50)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_trend_sensor").state == "on"
