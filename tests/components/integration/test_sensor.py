"""The tests for the integration sensor platform."""

from datetime import timedelta
from typing import Any

from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.integration.const import DOMAIN
from menuai.components.sensor import SensorDeviceClass, SensorStateClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfDataRate,
    UnitOfEnergy,
    UnitOfInformation,
    UnitOfPower,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from menuai.core import menuai, State
from menuai.helpers import (
    condition,
    device_registry as dr,
    entity_registry as er,
)
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

DEFAULT_MAX_SUB_INTERVAL = {"minutes": 1}


@pytest.mark.parametrize(
    ("unit_of_measurement", "device_class", "unit_time"),
    [
        (UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, "h"),
        (UnitOfPower.KILO_WATT, None, "h"),
        (UnitOfPower.BTU_PER_HOUR, SensorDeviceClass.POWER, "h"),
        (
            UnitOfVolumeFlowRate.CUBIC_FEET_PER_MINUTE,
            SensorDeviceClass.VOLUME_FLOW_RATE,
            "min",
        ),
    ],
)
async def test_initial_state(
    menuai: menuai,
    unit_of_measurement: str,
    device_class: SensorDeviceClass,
    unit_time: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.source",
            "round": 2,
            "method": "left",
            "unit_time": unit_time,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)
    menuai.states.async_set(
        "sensor.source",
        "1",
        {
            ATTR_DEVICE_CLASS: device_class,
            ATTR_UNIT_OF_MEASUREMENT: unit_of_measurement,
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.integration") == snapshot


@pytest.mark.parametrize("method", ["trapezoidal", "left", "right"])
async def test_state(menuai: menuai, method) -> None:
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
            "method": method,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.attributes.get("state_class") is SensorStateClass.TOTAL
    assert "device_class" not in state.attributes

    now = dt_util.utcnow()
    with freeze_time(now):
        entity_id = config["sensor"]["source"]
        menuai.states.async_set(
            entity_id,
            1,
            {
                ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT,
            },
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.attributes.get("state_class") is SensorStateClass.TOTAL
    assert "device_class" not in state.attributes

    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1,
            {
                "device_class": SensorDeviceClass.POWER,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT,
            },
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None

    # Testing a power sensor at 1 KiloWatts for 1hour = 1kWh
    assert round(float(state.state), config["sensor"]["round"]) == 1.0

    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.KILO_WATT_HOUR
    assert state.attributes.get("device_class") == SensorDeviceClass.ENERGY
    assert state.attributes.get("state_class") is SensorStateClass.TOTAL

    # 1 hour after last update, power sensor is unavailable
    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            STATE_UNAVAILABLE,
            {
                "device_class": SensorDeviceClass.POWER,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT,
            },
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state.state == STATE_UNAVAILABLE

    # 1 hour after last update, power sensor is back to normal at 2 KiloWatts and stays for 1 hour += 2kWh
    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            2,
            {
                "device_class": SensorDeviceClass.POWER,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT,
            },
            force_update=True,
        )
        await menuai.async_block_till_done()
    state = menuai.states.get("sensor.integration")
    assert (
        round(float(state.state), config["sensor"]["round"]) == 3.0
        if method == "right"
        else 1.0
    )

    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            2,
            {
                "device_class": SensorDeviceClass.POWER,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT,
            },
            force_update=True,
        )
        await menuai.async_block_till_done()
    state = menuai.states.get("sensor.integration")
    assert (
        round(float(state.state), config["sensor"]["round"]) == 5.0
        if method == "right"
        else 3.0
    )


async def test_restore_state(menuai: menuai) -> None:
    """Test integration sensor state is restored correctly."""
    mock_restore_cache_with_extra_data(
        menuai,
        [
            (
                State(
                    "sensor.integration",
                    STATE_UNAVAILABLE,
                    {
                        "device_class": SensorDeviceClass.ENERGY,
                        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
                    },
                ),
                {
                    "native_value": None,
                    "native_unit_of_measurement": "kWh",
                    "source_entity": "sensor.power",
                    "last_valid_state": "100.00",
                },
            ),
        ],
    )
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state
    assert state.state == "100.00"


@pytest.mark.parametrize(
    "extra_attributes",
    [
        {
            "native_unit_of_measurement": "kWh",
            "source_entity": "sensor.power",
            "last_valid_state": "100.00",
        },
        {
            "native_value": None,
            "native_unit_of_measurement": "kWh",
            "source_entity": "sensor.power",
            "last_valid_state": "None",
        },
    ],
)
async def test_restore_state_failed(menuai: menuai, extra_attributes) -> None:
    """Test integration sensor state is restored correctly."""
    mock_restore_cache_with_extra_data(
        menuai,
        [
            (
                State(
                    "sensor.integration",
                    STATE_UNAVAILABLE,
                    {
                        "device_class": SensorDeviceClass.ENERGY,
                        "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
                    },
                ),
                extra_attributes,
            ),
        ],
    )
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize("force_update", [False, True])
@pytest.mark.parametrize(
    "sequence",
    [
        (
            (20, 10, 1.67),
            (30, 30, 5.0),
            (40, 5, 7.92),
            (50, 5, 8.75),
            (60, 0, 9.17),
        ),
    ],
)
async def test_trapezoidal(
    menuai: menuai,
    sequence: tuple[tuple[float, float, float], ...],
    force_update: bool,
) -> None:
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(entity_id, 0, {})
    await menuai.async_block_till_done()

    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        # Testing a power sensor with non-monotonic intervals and values
        for time, value, expected in sequence:
            freezer.move_to(start_time + timedelta(minutes=time))
            menuai.states.async_set(
                entity_id,
                value,
                {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT},
                force_update=force_update,
            )
            await menuai.async_block_till_done()
            state = menuai.states.get("sensor.integration")
            assert round(float(state.state), config["sensor"]["round"]) == expected

    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.KILO_WATT_HOUR


@pytest.mark.parametrize("force_update", [False, True])
@pytest.mark.parametrize(
    "sequence",
    [
        (
            (20, 10, 0.0),
            (30, 30, 1.67),
            (40, 5, 6.67),
            (50, 5, 7.5),
            (60, 0, 8.33),
        ),
    ],
)
async def test_left(
    menuai: menuai,
    sequence: tuple[tuple[float, float, float], ...],
    force_update: bool,
) -> None:
    """Test integration sensor state with left reimann method."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "method": "left",
            "source": "sensor.power",
            "round": 2,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(
        entity_id, 0, {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT}
    )
    await menuai.async_block_till_done()

    # Testing a power sensor with non-monotonic intervals and values
    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        for time, value, expected in sequence:
            freezer.move_to(start_time + timedelta(minutes=time))
            menuai.states.async_set(
                entity_id,
                value,
                {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT},
                force_update=force_update,
            )
            await menuai.async_block_till_done()
            state = menuai.states.get("sensor.integration")
            assert round(float(state.state), config["sensor"]["round"]) == expected

    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.KILO_WATT_HOUR


@pytest.mark.parametrize("force_update", [False, True])
@pytest.mark.parametrize(
    "sequence",
    [
        (
            (20, 10, 3.33),
            (30, 30, 8.33),
            (40, 5, 9.17),
            (50, 5, 10.0),
            (60, 0, 10.0),
        ),
    ],
)
async def test_right(
    menuai: menuai,
    sequence: tuple[tuple[float, float, float], ...],
    force_update: bool,
) -> None:
    """Test integration sensor state with left reimann method."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "method": "right",
            "source": "sensor.power",
            "round": 2,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(
        entity_id, 0, {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT}
    )
    await menuai.async_block_till_done()

    # Testing a power sensor with non-monotonic intervals and values
    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        for time, value, expected in sequence:
            freezer.move_to(start_time + timedelta(minutes=time))
            menuai.states.async_set(
                entity_id,
                value,
                {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT},
                force_update=force_update,
            )
            await menuai.async_block_till_done()
            state = menuai.states.get("sensor.integration")
            assert round(float(state.state), config["sensor"]["round"]) == expected

    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.KILO_WATT_HOUR


async def test_prefix(menuai: menuai) -> None:
    """Test integration sensor state using a power source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
            "unit_prefix": "k",
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(entity_id, 1000, {"unit_of_measurement": UnitOfPower.WATT})
    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1000,
            {"unit_of_measurement": UnitOfPower.WATT},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None

    # Testing a power sensor at 1000 Watts for 1hour = 1kWh
    assert round(float(state.state), config["sensor"]["round"]) == 1.0
    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.KILO_WATT_HOUR


async def test_suffix(menuai: menuai) -> None:
    """Test integration sensor state using a network counter source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.bytes_per_second",
            "round": 2,
            "unit_prefix": "k",
            "unit_time": UnitOfTime.SECONDS,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(
        entity_id, 1000, {ATTR_UNIT_OF_MEASUREMENT: UnitOfDataRate.BYTES_PER_SECOND}
    )
    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1000,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfDataRate.BYTES_PER_SECOND},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None

    # Testing a network speed sensor at 1000 bytes/s over 10s  = 10kbytes
    assert round(float(state.state)) == 10
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfInformation.KILOBYTES


async def test_suffix_2(menuai: menuai) -> None:
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.cubic_meters_per_hour",
            "round": 2,
            "unit_time": UnitOfTime.HOURS,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    menuai.states.async_set(entity_id, 1000, {ATTR_UNIT_OF_MEASUREMENT: "m³/h"})
    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(hours=1)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1000,
            {ATTR_UNIT_OF_MEASUREMENT: "m³/h"},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None

    # Testing a flow sensor at 1000 m³/h over 1h = 1000 m³
    assert round(float(state.state)) == 1000
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "m³"


async def test_units(menuai: menuai) -> None:
    """Test integration sensor units using a power source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    # This replicates the current sequence when HA starts up in a real runtime
    # by updating the base sensor state before the base sensor's units
    # or state have been correctly populated.  Those interim updates
    # include states of None and Unknown
    menuai.states.async_set(entity_id, 100, {"unit_of_measurement": None})
    await menuai.async_block_till_done()
    menuai.states.async_set(entity_id, 200, {"unit_of_measurement": None})
    await menuai.async_block_till_done()
    menuai.states.async_set(entity_id, 300, {"unit_of_measurement": UnitOfPower.WATT})
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None

    # Testing the sensor ignored the source sensor's units until
    # they became valid
    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.WATT_HOUR

    # When source state goes to None / Unknown, expect an early exit without
    # changes to the state or unit_of_measurement
    menuai.states.async_set(entity_id, None, {"unit_of_measurement": UnitOfPower.WATT})
    await menuai.async_block_till_done()

    new_state = menuai.states.get("sensor.integration")
    assert state == new_state
    assert state.attributes.get("unit_of_measurement") == UnitOfEnergy.WATT_HOUR

    # When source state goes to unavailable, expect sensor to also become unavailable
    menuai.states.async_set(entity_id, STATE_UNAVAILABLE, None)
    await menuai.async_block_till_done()

    new_state = menuai.states.get("sensor.integration")
    assert new_state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("method", ["trapezoidal", "left", "right"])
async def test_device_class(menuai: menuai, method) -> None:
    """Test integration sensor units using a power source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "method": method,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]
    # This replicates the current sequence when HA starts up in a real runtime
    # by updating the base sensor state before the base sensor's units
    # or state have been correctly populated.  Those interim updates
    # include states of None and Unknown
    menuai.states.async_set(entity_id, STATE_UNKNOWN, {})
    await menuai.async_block_till_done()
    menuai.states.async_set(
        entity_id, 100, {"device_class": None, "unit_of_measurement": None}
    )
    await menuai.async_block_till_done()
    menuai.states.async_set(
        entity_id, 200, {"device_class": None, "unit_of_measurement": None}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert "device_class" not in state.attributes

    menuai.states.async_set(
        entity_id,
        300,
        {
            "device_class": SensorDeviceClass.POWER,
            "unit_of_measurement": UnitOfPower.WATT,
        },
        force_update=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    # Testing the sensor ignored the source sensor's device class until
    # it became valid
    assert state.attributes.get("device_class") == SensorDeviceClass.ENERGY


@pytest.mark.parametrize(
    ("method", "expected_states"),
    [
        ("trapezoidal", [STATE_UNKNOWN, "0.500", "0.500"]),
        ("left", [STATE_UNKNOWN, "0.000", "1.000"]),
        ("right", ["0.000", "1.000", "1.000"]),
    ],
)
async def test_calc_errors(
    menuai: menuai, method: str, expected_states: list[str]
) -> None:
    """Test integration sensor units using a power source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "method": method,
        }
    }

    assert await async_setup_component(menuai, "sensor", config)

    entity_id = config["sensor"]["source"]

    now = dt_util.utcnow()
    menuai.states.async_set(entity_id, None, {})
    await menuai.async_block_till_done()

    # With the source sensor in a None state, the Reimann sensor should be
    # unknown
    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    # Moving from an unknown state to a value is a calc error and should
    # not change the value of the Reimann sensor, unless the method used is "right".
    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(entity_id, 0, {"device_class": None})
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.state == expected_states[0]

    # With the source sensor updated successfully, the Reimann sensor
    # should have a zero (known) value.
    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(entity_id, 1, {"device_class": None})
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.state == expected_states[1]

    # Set the source sensor back to a non numeric state
    now += timedelta(seconds=3600)
    with freeze_time(now):
        menuai.states.async_set(entity_id, "unexpected", {"device_class": None})
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.integration")
    assert state is not None
    assert state.state == expected_states[2]


async def test_device_id(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for source entity device for Riemann sum integral."""
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

    integration_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "method": "trapezoidal",
            "name": "integration",
            "round": 1.0,
            "source": "sensor.test_source",
            "unit_prefix": "k",
            "unit_time": "min",
        },
        title="Integration",
    )

    integration_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(integration_config_entry.entry_id)
    await menuai.async_block_till_done()

    integration_entity = entity_registry.async_get("sensor.integration")
    assert integration_entity is not None
    assert integration_entity.device_id == source_entity.device_id


def _integral_sensor_config(max_sub_interval: dict[str, int] | None) -> dict[str, Any]:
    sensor = {
        "platform": "integration",
        "name": "integration",
        "source": "sensor.power",
        "method": "right",
    }
    if max_sub_interval is not None:
        sensor["max_sub_interval"] = max_sub_interval
    return {"sensor": sensor}


async def _setup_integral_sensor(
    menuai: menuai, max_sub_interval: dict[str, int] | None
) -> None:
    await async_setup_component(
        menuai, "sensor", _integral_sensor_config(max_sub_interval=max_sub_interval)
    )
    await menuai.async_block_till_done()


async def _update_source_sensor(menuai: menuai, value: int | str) -> None:
    menuai.states.async_set(
        _integral_sensor_config(max_sub_interval=DEFAULT_MAX_SUB_INTERVAL)["sensor"][
            "source"
        ],
        value,
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfPower.KILO_WATT},
        force_update=True,
    )
    await menuai.async_block_till_done()


async def test_on_valid_source_expect_update_on_time(
    menuai: menuai,
) -> None:
    """Test whether time based integration updates the integral on a valid source."""
    start_time = dt_util.utcnow()

    with freeze_time(start_time) as freezer:
        await _setup_integral_sensor(menuai, max_sub_interval=DEFAULT_MAX_SUB_INTERVAL)
        await _update_source_sensor(menuai, 100)
        state_before_max_sub_interval_exceeded = menuai.states.get("sensor.integration")

        freezer.tick(61)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.integration")
        assert (
            condition.async_numeric_state(menuai, state_before_max_sub_interval_exceeded)
            is False
        )
        assert state_before_max_sub_interval_exceeded.state != state.state
        assert condition.async_numeric_state(menuai, state) is True
        assert float(state.state) > 1.69  # approximately 100 * 61 / 3600
        assert float(state.state) < 1.8


async def test_on_0_source_expect_0_and_update_when_source_gets_positive(
    menuai: menuai,
) -> None:
    """Test whether time based integration updates the integral on a valid zero source."""
    start_time = dt_util.utcnow()

    with freeze_time(start_time) as freezer:
        await _setup_integral_sensor(menuai, max_sub_interval=DEFAULT_MAX_SUB_INTERVAL)
        await _update_source_sensor(menuai, 0)
        await menuai.async_block_till_done()

        # wait one minute and one second
        freezer.tick(61)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.integration")

        assert condition.async_numeric_state(menuai, state) is True
        assert float(state.state) == 0  # integral is 0 after integration of 0

        # wait one second and update state
        freezer.tick(1)
        async_fire_time_changed(menuai, dt_util.now())
        await _update_source_sensor(menuai, 100)
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.integration")

        # approx 100*1/3600 (right method after 1 second since last integration)
        assert 0.027 < float(state.state) < 0.029


async def test_on_unvailable_source_expect_no_update_on_time(
    menuai: menuai,
) -> None:
    """Test whether time based integration handles unavailability of the source properly."""

    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        await _setup_integral_sensor(menuai, max_sub_interval=DEFAULT_MAX_SUB_INTERVAL)
        await _update_source_sensor(menuai, 100)
        freezer.tick(61)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.integration")
        assert condition.async_numeric_state(menuai, state) is True

        await _update_source_sensor(menuai, STATE_UNAVAILABLE)
        await menuai.async_block_till_done()

        freezer.tick(61)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.integration")
        assert condition.state(menuai, state, STATE_UNAVAILABLE) is True


async def test_on_statechanges_source_expect_no_update_on_time(
    menuai: menuai,
) -> None:
    """Test whether state changes cancel time based integration."""

    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        await _setup_integral_sensor(menuai, max_sub_interval=DEFAULT_MAX_SUB_INTERVAL)
        await _update_source_sensor(menuai, 100)

        freezer.tick(30)
        await menuai.async_block_till_done()
        await _update_source_sensor(menuai, 101)

        state_after_30s = menuai.states.get("sensor.integration")
        assert condition.async_numeric_state(menuai, state_after_30s) is True

        freezer.tick(35)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()
        state_after_65s = menuai.states.get("sensor.integration")
        assert (dt_util.now() - start_time).total_seconds() > 60
        # No state change because the timer was cancelled because of an update after 30s
        assert state_after_65s == state_after_30s

        freezer.tick(35)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()
        state_after_105s = menuai.states.get("sensor.integration")
        # Update based on time
        assert float(state_after_105s.state) > float(state_after_65s.state)


async def test_on_no_max_sub_interval_expect_no_timebased_updates(
    menuai: menuai,
) -> None:
    """Test whether integratal is not updated by time when max_sub_interval is not configured."""

    start_time = dt_util.utcnow()
    with freeze_time(start_time) as freezer:
        await _setup_integral_sensor(menuai, max_sub_interval=None)
        await _update_source_sensor(menuai, 100)
        await menuai.async_block_till_done()
        await _update_source_sensor(menuai, 101)
        await menuai.async_block_till_done()

        state_after_last_state_change = menuai.states.get("sensor.integration")

        assert (
            condition.async_numeric_state(menuai, state_after_last_state_change) is True
        )

        freezer.tick(100)
        async_fire_time_changed(menuai, dt_util.now())
        await menuai.async_block_till_done()
        state_after_100s = menuai.states.get("sensor.integration")
        assert state_after_100s == state_after_last_state_change
