"""The tests for the utility_meter sensor platform."""

from datetime import timedelta

from freezegun import freeze_time
import pytest

from menuai.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from menuai.components.utility_meter import DEFAULT_OFFSET
from menuai.components.utility_meter.const import (
    ATTR_VALUE,
    DAILY,
    DOMAIN,
    HOURLY,
    QUARTER_HOURLY,
    SERVICE_CALIBRATE_METER,
    SERVICE_RESET,
)
from menuai.components.utility_meter.sensor import (
    ATTR_LAST_RESET,
    ATTR_STATUS,
    COLLECTING,
    PAUSED,
    UtilityMeterSensor,
)
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_menuai_STARTED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfVolume,
)
from menuai.core import CoreState, menuai, State
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.event import async_track_state_change_event
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)


@pytest.fixture(autouse=True)
async def set_utc(menuai: menuai):
    """Set timezone to UTC."""
    await menuai.config.async_set_time_zone("UTC")


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "tariffs": ["onpeak", "midpeak", "offpeak"],
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": ["onpeak", "midpeak", "offpeak"],
            },
        ),
    ],
)
async def test_state(menuai: menuai, yaml_config, config_entry_config) -> None:
    """Test utility sensor state."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == COLLECTING
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    state = menuai.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "1"
    assert state.attributes.get("status") == COLLECTING

    state = menuai.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED

    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.energy_bill", "option": "offpeak"},
        blocking=True,
    )

    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=20)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            6,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "1"
    assert state.attributes.get("status") == PAUSED

    state = menuai.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED

    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "3"
    assert state.attributes.get("status") == COLLECTING

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_CALIBRATE_METER,
        {ATTR_ENTITY_ID: "sensor.energy_bill_midpeak", ATTR_VALUE: "100"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "100"

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_CALIBRATE_METER,
        {ATTR_ENTITY_ID: "sensor.energy_bill_midpeak", ATTR_VALUE: "0.123"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0.123"

    # test invalid state
    menuai.states.async_set(
        entity_id, "*", {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "3"

    # test unavailable source
    menuai.states.async_set(
        entity_id,
        STATE_UNAVAILABLE,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "unavailable"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "always_available": True,
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": [],
                "always_available": True,
            },
        ),
    ],
)
async def test_state_always_available(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test utility sensor state."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == COLLECTING
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None
    assert state.state == "1"
    assert state.attributes.get("status") == COLLECTING

    # test unavailable state
    menuai.states.async_set(
        entity_id,
        "unavailable",
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill")
    assert state is not None
    assert state.state == "1"

    # test unknown state
    menuai.states.async_set(
        entity_id, None, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill")
    assert state is not None
    assert state.state == "1"


@pytest.mark.parametrize(
    "yaml_config",
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "tariffs": ["onpeak", "onpeak"],
                    }
                }
            },
            None,
        ),
    ],
)
async def test_not_unique_tariffs(menuai: menuai, yaml_config) -> None:
    """Test utility sensor state initialization."""
    assert not await async_setup_component(menuai, DOMAIN, yaml_config)


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "tariffs": ["onpeak", "midpeak", "offpeak"],
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": ["onpeak", "midpeak", "offpeak"],
            },
        ),
    ],
)
async def test_init(menuai: menuai, yaml_config, config_entry_config) -> None:
    """Test utility sensor state initialization."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )

    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    state = menuai.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR


async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique_id configuration option."""
    yaml_config = {
        "utility_meter": {
            "energy_bill": {
                "name": "Provider A",
                "unique_id": "1",
                "source": "sensor.energy",
                "tariffs": ["onpeak", "midpeak", "offpeak"],
            }
        }
    }
    assert await async_setup_component(menuai, DOMAIN, yaml_config)
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    assert len(entity_registry.entities) == 4
    assert entity_registry.entities["select.energy_bill"].unique_id == "1"
    assert entity_registry.entities["sensor.energy_bill_onpeak"].unique_id == "1_onpeak"


@pytest.mark.parametrize(
    ("yaml_config", "entity_id", "name"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "name": "dog",
                        "source": "sensor.energy",
                        "tariffs": ["onpeak", "midpeak", "offpeak"],
                    }
                }
            },
            "sensor.energy_bill_onpeak",
            "dog onpeak",
        ),
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "name": "dog",
                        "source": "sensor.energy",
                    }
                }
            },
            "sensor.dog",
            "dog",
        ),
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                    }
                }
            },
            "sensor.energy_bill",
            "energy_bill",
        ),
    ],
)
async def test_entity_name(menuai: menuai, yaml_config, entity_id, name) -> None:
    """Test utility sensor state initialization."""
    assert await async_setup_component(menuai, DOMAIN, yaml_config)
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert state.name == name


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_configs"),
    [
        (
            {
                "utility_meter": {
                    "energy_meter": {
                        "source": "sensor.energy",
                        "net_consumption": True,
                    },
                    "gas_meter": {
                        "source": "sensor.gas",
                    },
                }
            },
            None,
        ),
        (
            None,
            [
                {
                    "cycle": "none",
                    "delta_values": False,
                    "name": "Energy meter",
                    "net_consumption": True,
                    "offset": 0,
                    "periodically_resetting": True,
                    "source": "sensor.energy",
                    "tariffs": [],
                },
                {
                    "cycle": "none",
                    "delta_values": False,
                    "name": "Gas meter",
                    "net_consumption": False,
                    "offset": 0,
                    "periodically_resetting": True,
                    "source": "sensor.gas",
                    "tariffs": [],
                },
            ],
        ),
    ],
)
@pytest.mark.parametrize(
    (
        "energy_sensor_attributes",
        "gas_sensor_attributes",
        "energy_meter_attributes",
        "gas_meter_attributes",
    ),
    [
        (
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            {ATTR_UNIT_OF_MEASUREMENT: "some_archaic_unit"},
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.ENERGY,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR,
            },
            {
                ATTR_DEVICE_CLASS: None,
                ATTR_UNIT_OF_MEASUREMENT: "some_archaic_unit",
            },
        ),
        (
            {},
            {},
            {
                ATTR_DEVICE_CLASS: None,
                ATTR_UNIT_OF_MEASUREMENT: None,
            },
            {
                ATTR_DEVICE_CLASS: None,
                ATTR_UNIT_OF_MEASUREMENT: None,
            },
        ),
        (
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.GAS,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR,
            },
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.WATER,
                ATTR_UNIT_OF_MEASUREMENT: "some_archaic_unit",
            },
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.GAS,
                ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR,
            },
            {
                ATTR_DEVICE_CLASS: SensorDeviceClass.WATER,
                ATTR_UNIT_OF_MEASUREMENT: "some_archaic_unit",
            },
        ),
    ],
)
async def test_device_class(
    menuai: menuai,
    yaml_config,
    config_entry_configs,
    energy_sensor_attributes,
    gas_sensor_attributes,
    energy_meter_attributes,
    gas_meter_attributes,
) -> None:
    """Test utility device_class."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
    else:
        for config_entry_config in config_entry_configs:
            config_entry = MockConfigEntry(
                data={},
                domain=DOMAIN,
                options=config_entry_config,
                title=config_entry_config["name"],
            )
            config_entry.add_to_menuai(menuai)
            assert await menuai.config_entries.async_setup(config_entry.entry_id)
            await menuai.async_block_till_done()

    entity_id_energy = "sensor.energy"
    entity_id_gas = "sensor.gas"

    menuai.bus.async_fire(EVENT_menuai_STARTED)

    await menuai.async_block_till_done()

    menuai.states.async_set(entity_id_energy, 2, energy_sensor_attributes)
    menuai.states.async_set(entity_id_gas, 2, gas_sensor_attributes)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_meter")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL
    for attr, value in energy_meter_attributes.items():
        assert state.attributes.get(attr) == value

    state = menuai.states.get("sensor.gas_meter")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL_INCREASING
    for attr, value in gas_meter_attributes.items():
        assert state.attributes.get(attr) == value


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "tariffs": [
                            "tariff0",
                            "tariff1",
                            "tariff2",
                            "tariff3",
                            "tariff4",
                        ],
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": [
                    "tariff0",
                    "tariff1",
                    "tariff2",
                    "tariff3",
                    "tariff4",
                ],
            },
        ),
    ],
)
async def test_restore_state(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test utility sensor restore state."""
    # MenuAI is not runnit yet
    menuai.set_state(CoreState.not_running)

    last_reset_1 = "2020-12-21T00:00:00.013073+00:00"
    last_reset_2 = "2020-12-22T00:00:00.013073+00:00"

    mock_restore_cache_with_extra_data(
        menuai,
        [
            # sensor.energy_bill_tariff0 is restored as expected, including device
            # class
            (
                State(
                    "sensor.energy_bill_tariff0",
                    "0.1",
                    attributes={
                        ATTR_STATUS: PAUSED,
                        ATTR_LAST_RESET: last_reset_1,
                        ATTR_UNIT_OF_MEASUREMENT: UnitOfVolume.CUBIC_METERS,
                    },
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "0.2",
                    },
                    "native_unit_of_measurement": "gal",
                    "last_reset": last_reset_2,
                    "last_period": "1.3",
                    "last_valid_state": None,
                    "status": "collecting",
                    "input_device_class": "water",
                },
            ),
            # sensor.energy_bill_tariff1 is restored as expected, except device
            # class
            (
                State(
                    "sensor.energy_bill_tariff1",
                    "1.1",
                    attributes={
                        ATTR_STATUS: PAUSED,
                        ATTR_LAST_RESET: last_reset_1,
                        ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.MEGA_WATT_HOUR,
                    },
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "1.2",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset_2,
                    "last_period": "1.3",
                    "last_valid_state": None,
                    "status": "paused",
                },
            ),
        ],
    )

    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    # restore from cache
    state = menuai.states.get("sensor.energy_bill_tariff0")
    assert state.state == "0.2"
    assert state.attributes.get("status") == COLLECTING
    assert state.attributes.get("last_reset") == last_reset_2
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfVolume.GALLONS
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.WATER

    state = menuai.states.get("sensor.energy_bill_tariff1")
    assert state.state == "1.2"
    assert state.attributes.get("status") == PAUSED
    assert state.attributes.get("last_reset") == last_reset_2
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.ENERGY

    # utility_meter is loaded, now set sensors according to utility_meter:

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    state = menuai.states.get("select.energy_bill")
    assert state.state == "tariff0"

    state = menuai.states.get("sensor.energy_bill_tariff0")
    assert state.attributes.get("status") == COLLECTING

    for entity_id in ("sensor.energy_bill_tariff1",):
        state = menuai.states.get(entity_id)
        assert state.attributes.get("status") == PAUSED


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": [],
            },
        ),
    ],
)
async def test_service_reset_no_tariffs(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test utility sensor service reset for sensor with no tariffs."""
    # MenuAI is not runnit yet
    menuai.state = CoreState.not_running
    last_reset = "2023-10-01T00:00:00+00:00"

    mock_restore_cache_with_extra_data(
        menuai,
        [
            (
                State(
                    "sensor.energy_bill",
                    "3",
                    attributes={
                        ATTR_LAST_RESET: last_reset,
                    },
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "3",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset,
                    "last_period": "0",
                    "last_valid_state": None,
                    "status": "collecting",
                    "input_device_class": "energy",
                },
            ),
        ],
    )

    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state
    assert state.state == "3"
    assert state.attributes.get("last_reset") == last_reset
    assert state.attributes.get("last_period") == "0"

    now = dt_util.utcnow()
    with freeze_time(now):
        await menuai.services.async_call(
            domain=DOMAIN,
            service=SERVICE_RESET,
            service_data={},
            target={"entity_id": "sensor.energy_bill"},
            blocking=True,
        )

        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state
    assert state.state == "0"
    assert state.attributes.get("last_reset") == now.isoformat()
    assert state.attributes.get("last_period") == "3"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_configs"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                    },
                    "water_bill": {
                        "source": "sensor.water",
                    },
                },
            },
            None,
        ),
        (
            None,
            [
                {
                    "cycle": "none",
                    "delta_values": False,
                    "name": "Energy bill",
                    "net_consumption": False,
                    "offset": 0,
                    "periodically_resetting": True,
                    "source": "sensor.energy",
                    "tariffs": [],
                },
                {
                    "cycle": "none",
                    "delta_values": False,
                    "name": "Water bill",
                    "net_consumption": False,
                    "offset": 0,
                    "periodically_resetting": True,
                    "source": "sensor.water",
                    "tariffs": [],
                },
            ],
        ),
    ],
)
async def test_service_reset_no_tariffs_correct_with_multi(
    menuai: menuai, yaml_config, config_entry_configs
) -> None:
    """Test complex utility sensor service reset for multiple sensors with no tarrifs.

    See GitHub issue #114864: Service "utility_meter.reset" affects all meters.
    """

    # MenuAI is not runnit yet
    menuai.state = CoreState.not_running
    last_reset = "2023-10-01T00:00:00+00:00"

    mock_restore_cache_with_extra_data(
        menuai,
        [
            (
                State(
                    "sensor.energy_bill",
                    "3",
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "3",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset,
                    "last_period": "0",
                    "status": "collecting",
                },
            ),
            (
                State(
                    "sensor.water_bill",
                    "6",
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "6",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset,
                    "last_period": "0",
                    "status": "collecting",
                },
            ),
        ],
    )

    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
    else:
        for entry in config_entry_configs:
            config_entry = MockConfigEntry(
                data={},
                domain=DOMAIN,
                options=entry,
                title=entry["name"],
            )
            config_entry.add_to_menuai(menuai)
            assert await menuai.config_entries.async_setup(config_entry.entry_id)
            await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state
    assert state.state == "3"
    assert state.attributes.get("last_reset") == last_reset
    assert state.attributes.get("last_period") == "0"

    state = menuai.states.get("sensor.water_bill")
    assert state
    assert state.state == "6"
    assert state.attributes.get("last_reset") == last_reset
    assert state.attributes.get("last_period") == "0"

    now = dt_util.utcnow()
    with freeze_time(now):
        await menuai.services.async_call(
            domain=DOMAIN,
            service=SERVICE_RESET,
            service_data={},
            target={"entity_id": "sensor.energy_bill"},
            blocking=True,
        )

        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state
    assert state.state == "0"
    assert state.attributes.get("last_reset") == now.isoformat()
    assert state.attributes.get("last_period") == "3"

    state = menuai.states.get("sensor.water_bill")
    assert state
    assert state.state == "6"
    assert state.attributes.get("last_reset") == last_reset
    assert state.attributes.get("last_period") == "0"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "net_consumption": True,
                        "source": "sensor.energy",
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": True,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": [],
            },
        ),
    ],
)
async def test_net_consumption(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test utility sensor state."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None

    assert state.state == "-1"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "net_consumption": False,
                        "source": "sensor.energy",
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "source": "sensor.energy",
                "tariffs": [],
            },
        ),
    ],
)
async def test_non_net_consumption(
    menuai: menuai,
    yaml_config,
    config_entry_config,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test utility sensor state."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            1,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            None,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()
    assert "invalid new state " in caplog.text

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None

    assert state.state == "0"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "delta_values": True,
                        "source": "sensor.energy",
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": True,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": True,
                "source": "sensor.energy",
                "tariffs": [],
            },
        ),
    ],
)
async def test_delta_values(
    menuai: menuai,
    yaml_config,
    config_entry_config,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test utility meter "delta_values" mode."""
    # MenuAI is not runnit yet
    menuai.set_state(CoreState.not_running)

    now = dt_util.utcnow()
    with freeze_time(now):
        if yaml_config:
            assert await async_setup_component(menuai, DOMAIN, yaml_config)
            await menuai.async_block_till_done()
            entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
        else:
            config_entry = MockConfigEntry(
                data={},
                domain=DOMAIN,
                options=config_entry_config,
                title=config_entry_config["name"],
            )
            config_entry.add_to_menuai(menuai)
            assert await menuai.config_entries.async_setup(config_entry.entry_id)
            await menuai.async_block_till_done()
            entity_id = config_entry_config["source"]

        menuai.bus.async_fire(EVENT_menuai_STARTED)

        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id, 1, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            None,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()
    assert "invalid new state from sensor.energy : None" in caplog.text

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()
        menuai.states.async_set(
            entity_id,
            6,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None

    assert state.state == "10"


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "periodically_resetting": False,
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": False,
                "source": "sensor.energy",
                "tariffs": [],
            },
        ),
    ],
)
async def test_non_periodically_resetting(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test utility meter "non periodically resetting" mode."""
    # MenuAI is not runnit yet
    menuai.set_state(CoreState.not_running)

    now = dt_util.utcnow()
    with freeze_time(now):
        if yaml_config:
            assert await async_setup_component(menuai, DOMAIN, yaml_config)
            await menuai.async_block_till_done()
            entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
        else:
            config_entry = MockConfigEntry(
                data={},
                domain=DOMAIN,
                options=config_entry_config,
                title=config_entry_config["name"],
                version=2,
            )
            config_entry.add_to_menuai(menuai)
            assert await menuai.config_entries.async_setup(config_entry.entry_id)
            await menuai.async_block_till_done()
            entity_id = config_entry_config["source"]

        menuai.bus.async_fire(EVENT_menuai_STARTED)

        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id, 1, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.state == "2"
    assert state.attributes.get("last_valid_state") == "3"
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            STATE_UNKNOWN,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.state == "2"
    assert state.attributes.get("last_valid_state") == "3"
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            6,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.state == "5"
    assert state.attributes.get("last_valid_state") == "6"
    assert state.attributes.get("status") == COLLECTING

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()
        menuai.states.async_set(
            entity_id,
            9,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state.state == "8"
    assert state.attributes.get("last_valid_state") == "9"
    assert state.attributes.get("status") == COLLECTING


@pytest.mark.parametrize(
    ("yaml_config", "config_entry_config"),
    [
        (
            {
                "utility_meter": {
                    "energy_bill": {
                        "source": "sensor.energy",
                        "periodically_resetting": False,
                        "tariffs": ["low", "high"],
                    }
                }
            },
            None,
        ),
        (
            None,
            {
                "cycle": "none",
                "delta_values": False,
                "name": "Energy bill",
                "net_consumption": False,
                "offset": 0,
                "periodically_resetting": False,
                "source": "sensor.energy",
                "tariffs": ["low", "high"],
            },
        ),
    ],
)
async def test_non_periodically_resetting_meter_with_tariffs(
    menuai: menuai, yaml_config, config_entry_config
) -> None:
    """Test test_non_periodically_resetting_meter_with_tariffs."""
    if yaml_config:
        assert await async_setup_component(menuai, DOMAIN, yaml_config)
        await menuai.async_block_till_done()
        entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]
    else:
        config_entry = MockConfigEntry(
            data={},
            domain=DOMAIN,
            options=config_entry_config,
            title=config_entry_config["name"],
            version=2,
        )
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        entity_id = config_entry_config["source"]

    menuai.bus.async_fire(EVENT_menuai_STARTED)

    await menuai.async_block_till_done()

    menuai.states.async_set(
        entity_id, 2, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_low")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == COLLECTING
    assert state.attributes.get("last_valid_state") == "2"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    state = menuai.states.get("sensor.energy_bill_high")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("status") == PAUSED
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfEnergy.KILO_WATT_HOUR

    now = dt_util.utcnow() + timedelta(seconds=10)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_low")
    assert state is not None
    assert state.state == "1"
    assert state.attributes.get("last_valid_state") == "3"
    assert state.attributes.get("status") == COLLECTING

    state = menuai.states.get("sensor.energy_bill_high")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get("status") == PAUSED

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.energy_bill", "option": "high"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_low")
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get("status") == PAUSED

    state = menuai.states.get("sensor.energy_bill_high")
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get("status") == COLLECTING

    now = dt_util.utcnow() + timedelta(seconds=20)
    with freeze_time(now):
        menuai.states.async_set(
            entity_id,
            6,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill_low")
    assert state is not None
    assert state.state == "1"
    assert state.attributes.get("last_valid_state") == "None"
    assert state.attributes.get("status") == PAUSED

    state = menuai.states.get("sensor.energy_bill_high")
    assert state is not None
    assert state.state == "3"
    assert state.attributes.get("last_valid_state") == "6"
    assert state.attributes.get("status") == COLLECTING


def gen_config(cycle, offset=None):
    """Generate configuration."""
    config = {
        "utility_meter": {"energy_bill": {"source": "sensor.energy", "cycle": cycle}}
    }

    if offset:
        config["utility_meter"]["energy_bill"]["offset"] = {
            "days": offset.days,
            "seconds": offset.seconds,
        }
    return config


async def _test_self_reset(
    menuai: menuai, config, start_time, expect_reset=True
) -> None:
    """Test energy sensor self reset."""
    now = dt_util.parse_datetime(start_time)
    with freeze_time(now):
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

        menuai.bus.async_fire(EVENT_menuai_STARTED)
        entity_id = config[DOMAIN]["energy_bill"]["source"]

        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id, 1, {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR}
        )
        await menuai.async_block_till_done()

    now += timedelta(seconds=30)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        menuai.states.async_set(
            entity_id,
            3,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    now += timedelta(seconds=30)
    with freeze_time(now):
        # Listen for events and check that state in the first event after reset is actually 0, issue #142053
        events = []

        async def handle_energy_bill_event(event):
            events.append(event)

        unsub = async_track_state_change_event(
            menuai,
            "sensor.energy_bill",
            handle_energy_bill_event,
        )

        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()
        unsub()
        menuai.states.async_set(
            entity_id,
            6,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    if expect_reset:
        assert state.attributes.get("last_period") == "2"
        assert (
            state.attributes.get("last_reset") == dt_util.as_utc(now).isoformat()
        )  # last_reset is kept in UTC
        assert state.state == "3"
        # In first event state should be 0
        assert len(events) == 2
        assert events[0].data.get("new_state").state == "0"
        assert events[1].data.get("new_state").state == "0"
    else:
        assert state.attributes.get("last_period") == "0"
        assert state.state == "5"
        start_time_str = dt_util.parse_datetime(start_time).isoformat()
        assert state.attributes.get("last_reset") == start_time_str

    # Check next day when nothing should happen for weekly, monthly, bimonthly and yearly
    if config["utility_meter"]["energy_bill"].get("cycle") in [
        QUARTER_HOURLY,
        HOURLY,
        DAILY,
    ]:
        now += timedelta(minutes=5)
    else:
        now += timedelta(days=5)
    with freeze_time(now):
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()
        menuai.states.async_set(
            entity_id,
            10,
            {ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR},
            force_update=True,
        )
        await menuai.async_block_till_done()
    state = menuai.states.get("sensor.energy_bill")
    if expect_reset:
        assert state.attributes.get("last_period") == "2"
        assert state.state == "7"
    else:
        assert state.attributes.get("last_period") == "0"
        assert state.state == "9"


async def test_self_reset_cron_pattern(menuai: menuai) -> None:
    """Test cron pattern reset of meter."""
    config = {
        "utility_meter": {
            "energy_bill": {"source": "sensor.energy", "cron": "0 0 1 * *"}
        }
    }

    await _test_self_reset(menuai, config, "2017-01-31T23:59:00.000000+00:00")


async def test_self_reset_quarter_hourly(menuai: menuai) -> None:
    """Test quarter-hourly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("quarter-hourly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_quarter_hourly_first_quarter(menuai: menuai) -> None:
    """Test quarter-hourly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("quarter-hourly"), "2017-12-31T23:14:00.000000+00:00"
    )


async def test_self_reset_quarter_hourly_second_quarter(menuai: menuai) -> None:
    """Test quarter-hourly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("quarter-hourly"), "2017-12-31T23:29:00.000000+00:00"
    )


async def test_self_reset_quarter_hourly_third_quarter(menuai: menuai) -> None:
    """Test quarter-hourly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("quarter-hourly"), "2017-12-31T23:44:00.000000+00:00"
    )


async def test_self_reset_hourly(menuai: menuai) -> None:
    """Test hourly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("hourly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_hourly_dst(menuai: menuai) -> None:
    """Test hourly reset of meter in DST change conditions."""

    menuai.config.time_zone = "Europe/Lisbon"
    dt_util.set_default_time_zone(dt_util.get_time_zone(menuai.config.time_zone))
    await _test_self_reset(
        menuai, gen_config("hourly"), "2023-10-29T01:59:00.000000+00:00"
    )


async def test_self_reset_hourly_dst2(menuai: menuai) -> None:
    """Test weekly reset of meter in DST change conditions."""

    menuai.config.time_zone = "Europe/Berlin"
    dt_util.set_default_time_zone(dt_util.get_time_zone(menuai.config.time_zone))
    await _test_self_reset(
        menuai, gen_config("daily"), "2024-10-26T23:59:00.000000+02:00"
    )

    state = menuai.states.get("sensor.energy_bill")
    last_reset = dt_util.parse_datetime("2024-10-27T00:00:00.000000+02:00")
    assert (
        dt_util.as_local(dt_util.parse_datetime(state.attributes.get("last_reset")))
        == last_reset
    )

    next_reset = dt_util.parse_datetime("2024-10-28T00:00:00.000000+01:00").isoformat()
    assert state.attributes.get("next_reset") == next_reset


async def test_tz_changes(menuai: menuai) -> None:
    """Test that a timezone change changes the scheduler."""

    await menuai.config.async_update(time_zone="Europe/Prague")

    await _test_self_reset(
        menuai, gen_config("daily"), "2024-10-26T23:59:00.000000+02:00"
    )
    state = menuai.states.get("sensor.energy_bill")
    assert state.attributes.get("next_reset") == "2024-10-28T00:00:00+01:00"

    await menuai.config.async_update(time_zone="Pacific/Fiji")

    state = menuai.states.get("sensor.energy_bill")
    assert state.attributes.get("next_reset") != "2024-10-28T00:00:00+01:00"


async def test_self_reset_daily(menuai: menuai) -> None:
    """Test daily reset of meter."""
    await _test_self_reset(
        menuai, gen_config("daily"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_weekly(menuai: menuai) -> None:
    """Test weekly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("weekly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_monthly(menuai: menuai) -> None:
    """Test monthly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("monthly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_bimonthly(menuai: menuai) -> None:
    """Test bimonthly reset of meter occurs on even months."""
    await _test_self_reset(
        menuai, gen_config("bimonthly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_no_reset_bimonthly(menuai: menuai) -> None:
    """Test bimonthly reset of meter does not occur on odd months."""
    await _test_self_reset(
        menuai,
        gen_config("bimonthly"),
        "2018-01-01T23:59:00.000000+00:00",
        expect_reset=False,
    )


async def test_self_reset_quarterly(menuai: menuai) -> None:
    """Test quarterly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("quarterly"), "2017-03-31T23:59:00.000000+00:00"
    )


async def test_self_reset_yearly(menuai: menuai) -> None:
    """Test yearly reset of meter."""
    await _test_self_reset(
        menuai, gen_config("yearly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_no_reset_yearly(menuai: menuai) -> None:
    """Test yearly reset of meter does not occur after 1st January."""
    await _test_self_reset(
        menuai,
        gen_config("yearly"),
        "2018-01-01T23:59:00.000000+00:00",
        expect_reset=False,
    )


async def test_reset_yearly_offset(menuai: menuai) -> None:
    """Test yearly reset of meter."""
    await _test_self_reset(
        menuai,
        gen_config("yearly", timedelta(days=1, minutes=10)),
        "2018-01-02T00:09:00.000000+00:00",
    )


async def test_no_reset_yearly_offset(menuai: menuai) -> None:
    """Test yearly reset of meter."""
    await _test_self_reset(
        menuai,
        gen_config("yearly", timedelta(27)),
        "2018-04-29T23:59:00.000000+00:00",
        expect_reset=False,
    )


async def test_bad_offset(menuai: menuai) -> None:
    """Test bad offset of meter."""
    assert not await async_setup_component(
        menuai, DOMAIN, gen_config("monthly", timedelta(days=31))
    )


def test_calculate_adjustment_invalid_new_state(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that calculate_adjustment method returns None if the new state is invalid."""
    mock_sensor = UtilityMeterSensor(
        cron_pattern=None,
        delta_values=False,
        meter_offset=DEFAULT_OFFSET,
        meter_type=DAILY,
        name="Test utility meter",
        net_consumption=False,
        parent_meter="sensor.test",
        periodically_resetting=True,
        sensor_always_available=False,
        unique_id="test_utility_meter",
        source_entity="sensor.test",
        tariff=None,
        tariff_entity=None,
    )

    new_state: State = State(entity_id="sensor.test", state="unknown")
    assert mock_sensor.calculate_adjustment(None, new_state) is None
    assert "Invalid state unknown" in caplog.text


async def test_unit_of_measurement_missing_invalid_new_state(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a suggestion is created when new_state is missing unit_of_measurement."""
    yaml_config = {
        "utility_meter": {
            "energy_bill": {
                "source": "sensor.energy",
            }
        }
    }
    source_entity_id = yaml_config[DOMAIN]["energy_bill"]["source"]

    assert await async_setup_component(menuai, DOMAIN, yaml_config)
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()

    menuai.states.async_set(source_entity_id, 4, {ATTR_UNIT_OF_MEASUREMENT: None})

    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.energy_bill")
    assert state is not None
    assert state.state == "0"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) is None
    assert (
        f"Source sensor {source_entity_id} has no unit of measurement." in caplog.text
    )


async def test_device_id(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for source entity device for Utility Meter."""
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

    utility_meter_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "cycle": "monthly",
            "delta_values": False,
            "name": "Energy",
            "net_consumption": False,
            "offset": 0,
            "periodically_resetting": True,
            "source": "sensor.test_source",
            "tariffs": ["peak", "offpeak"],
        },
        title="Energy",
    )

    utility_meter_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(utility_meter_config_entry.entry_id)
    await menuai.async_block_till_done()

    utility_meter_entity = entity_registry.async_get("sensor.energy_peak")
    assert utility_meter_entity is not None
    assert utility_meter_entity.device_id == source_entity.device_id

    utility_meter_entity = entity_registry.async_get("sensor.energy_offpeak")
    assert utility_meter_entity is not None
    assert utility_meter_entity.device_id == source_entity.device_id

    utility_meter_no_tariffs_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "cycle": "monthly",
            "delta_values": False,
            "name": "Energy",
            "net_consumption": False,
            "offset": 0,
            "periodically_resetting": True,
            "source": "sensor.test_source",
            "tariffs": [],
        },
        title="Energy",
    )

    utility_meter_no_tariffs_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(
        utility_meter_no_tariffs_config_entry.entry_id
    )
    await menuai.async_block_till_done()

    utility_meter_no_tariffs_entity = entity_registry.async_get("sensor.energy")
    assert utility_meter_no_tariffs_entity is not None
    assert utility_meter_no_tariffs_entity.device_id == source_entity.device_id
