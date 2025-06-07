"""The tests for the generic_thermostat."""

import datetime
from unittest.mock import patch

from freezegun import freeze_time
import pytest
import voluptuous as vol

from menuai import config as menuai_config, core as ha
from menuai.components import input_boolean, switch
from menuai.components.climate import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    HVACMode,
)
from menuai.components.generic_thermostat.const import DOMAIN
from menuai.const import (
    ATTR_TEMPERATURE,
    SERVICE_RELOAD,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from menuai.core import (
    DOMAIN as menuai_DOMAIN,
    CoreState,
    menuai,
    ServiceCall,
    State,
    callback,
)
from menuai.exceptions import ServiceValidationError
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.typing import StateType
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util
from menuai.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

from tests.common import (
    MockConfigEntry,
    assert_setup_component,
    async_fire_time_changed,
    async_mock_service,
    get_fixture_path,
    mock_restore_cache,
    setup_test_component_platform,
)
from tests.components.climate import common
from tests.components.switch.common import MockSwitch

ENTITY = "climate.test"
ENT_SENSOR = "sensor.test"
ENT_SWITCH = "switch.test"
HEAT_ENTITY = "climate.test_heat"
COOL_ENTITY = "climate.test_cool"
ATTR_AWAY_MODE = "away_mode"
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5
TARGET_TEMP_STEP = 0.5


async def test_setup_missing_conf(menuai: menuai) -> None:
    """Test set up heat_control with missing config values."""
    config = {
        "platform": "generic_thermostat",
        "name": "test",
        "target_sensor": ENT_SENSOR,
    }
    with assert_setup_component(0):
        await async_setup_component(menuai, "climate", {"climate": config})


async def test_valid_conf(menuai: menuai) -> None:
    """Test set up generic_thermostat with valid config values."""
    assert await async_setup_component(
        menuai,
        "climate",
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
            }
        },
    )


@pytest.fixture
async def setup_comp_1(menuai: menuai) -> None:
    """Initialize components."""
    menuai.config.units = METRIC_SYSTEM
    assert await async_setup_component(menuai, "menuai", {})
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_1")
async def test_heater_input_boolean(menuai: menuai) -> None:
    """Test heater switching input_boolean."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        menuai, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": heater_switch,
                "target_sensor": ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(menuai, 18)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 23)
    await menuai.async_block_till_done()

    assert menuai.states.get(heater_switch).state == STATE_ON


@pytest.mark.usefixtures("setup_comp_1")
async def test_heater_switch(
    menuai: menuai, mock_switch_entities: list[MockSwitch]
) -> None:
    """Test heater switching test switch."""
    setup_test_component_platform(menuai, switch.DOMAIN, mock_switch_entities)
    switch_1 = mock_switch_entities[1]
    assert await async_setup_component(
        menuai, switch.DOMAIN, {"switch": {"platform": "test"}}
    )
    await menuai.async_block_till_done()
    heater_switch = switch_1.entity_id

    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": heater_switch,
                "target_sensor": ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )

    await menuai.async_block_till_done()
    assert menuai.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(menuai, 18)
    await common.async_set_temperature(menuai, 23)
    await menuai.async_block_till_done()

    assert menuai.states.get(heater_switch).state == STATE_ON


@pytest.mark.usefixtures("setup_comp_1")
async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
    _setup_sensor(menuai, 18)
    _setup_switch(menuai, True)
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "unique_id": unique_id,
            }
        },
    )
    await menuai.async_block_till_done()

    entry = entity_registry.async_get(ENTITY)
    assert entry
    assert entry.unique_id == unique_id


def _setup_sensor(menuai: menuai, temp: StateType) -> None:
    """Set up the test sensor."""
    menuai.states.async_set(ENT_SENSOR, temp)


@pytest.fixture
async def setup_comp_2(menuai: menuai) -> None:
    """Initialize components."""
    menuai.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "away_temp": 16,
                "sleep_temp": 17,
                "home_temp": 19,
                "comfort_temp": 20,
                "eco_temp": 18,
                "activity_temp": 21,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await menuai.async_block_till_done()


async def test_setup_defaults_to_unknown(menuai: menuai) -> None:
    """Test the setting of defaults to unknown."""
    menuai.config.units = METRIC_SYSTEM
    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "away_temp": 16,
            }
        },
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temp_from_sensor(menuai: menuai) -> None:
    """Test that current temperature is updated on entity addition."""
    menuai.config.units = METRIC_SYSTEM
    _setup_sensor(menuai, 18)
    await menuai.async_block_till_done()
    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "away_temp": 16,
            }
        },
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(ENTITY).attributes["current_temperature"] == 18


@pytest.mark.usefixtures("setup_comp_2")
async def test_default_setup_params(menuai: menuai) -> None:
    """Test the setup with default parameters."""
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("temperature") == 7
    assert state.attributes.get("target_temp_step") == 0.1


@pytest.mark.usefixtures("setup_comp_2")
async def test_get_hvac_modes(menuai: menuai) -> None:
    """Test that the operation list returns the correct modes."""
    state = menuai.states.get(ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert modes == [HVACMode.HEAT, HVACMode.OFF]


@pytest.mark.usefixtures("setup_comp_2")
async def test_set_target_temp(menuai: menuai) -> None:
    """Test the setting of the target temperature."""
    await common.async_set_temperature(menuai, 30)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 30.0
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(menuai, None)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 30.0


@pytest.mark.usefixtures("setup_comp_2")
async def test_set_target_temp_change_preset(menuai: menuai) -> None:
    """Test the setting of the target temperature.

    Verify that preset is changed.
    """
    await common.async_set_temperature(menuai, 30)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_NONE
    await common.async_set_temperature(menuai, 20)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_COMFORT


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
    ],
)
@pytest.mark.usefixtures("setup_comp_2")
async def test_set_away_mode(menuai: menuai, preset, temp) -> None:
    """Test the setting away mode."""
    await common.async_set_temperature(menuai, 23)
    await common.async_set_preset_mode(menuai, preset)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == temp


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
    ],
)
@pytest.mark.usefixtures("setup_comp_2")
async def test_set_away_mode_and_restore_prev_temp(
    menuai: menuai, preset, temp
) -> None:
    """Test the setting and removing away mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(menuai, 23)
    await common.async_set_preset_mode(menuai, preset)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(menuai, PRESET_NONE)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
    ],
)
@pytest.mark.usefixtures("setup_comp_2")
async def test_set_away_mode_twice_and_restore_prev_temp(
    menuai: menuai, preset, temp
) -> None:
    """Test the setting away mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(menuai, 23)
    await common.async_set_preset_mode(menuai, preset)
    await common.async_set_preset_mode(menuai, preset)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == temp
    await common.async_set_preset_mode(menuai, PRESET_NONE)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 23


@pytest.mark.usefixtures("setup_comp_2")
async def test_set_preset_mode_invalid(menuai: menuai) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(menuai, 23)
    await common.async_set_preset_mode(menuai, "away")
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("preset_mode") == "away"
    await common.async_set_preset_mode(menuai, "none")
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("preset_mode") == "none"
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(menuai, "Sleep")
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("preset_mode") == "none"


@pytest.mark.usefixtures("setup_comp_2")
async def test_sensor_bad_value(menuai: menuai) -> None:
    """Test sensor that have None as state."""
    state = menuai.states.get(ENTITY)
    temp = state.attributes.get("current_temperature")

    _setup_sensor(menuai, None)
    await menuai.async_block_till_done()
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("current_temperature") == temp

    _setup_sensor(menuai, "inf")
    await menuai.async_block_till_done()
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("current_temperature") == temp

    _setup_sensor(menuai, "nan")
    await menuai.async_block_till_done()
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("current_temperature") == temp


async def test_sensor_unknown(menuai: menuai) -> None:
    """Test when target sensor is Unknown."""
    menuai.states.async_set("sensor.unknown", STATE_UNKNOWN)
    assert await async_setup_component(
        menuai,
        "climate",
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "unknown",
                "heater": ENT_SWITCH,
                "target_sensor": "sensor.unknown",
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.unknown")
    assert state.attributes.get("current_temperature") is None


async def test_sensor_unavailable(menuai: menuai) -> None:
    """Test when target sensor is Unavailable."""
    menuai.states.async_set("sensor.unavailable", STATE_UNAVAILABLE)
    assert await async_setup_component(
        menuai,
        "climate",
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "unavailable",
                "heater": ENT_SWITCH,
                "target_sensor": "sensor.unavailable",
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.unavailable")
    assert state.attributes.get("current_temperature") is None


@pytest.mark.usefixtures("setup_comp_2")
async def test_set_target_temp_heater_on(menuai: menuai) -> None:
    """Test if target temperature turn heater on."""
    calls = _setup_switch(menuai, False)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 30)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_2")
async def test_set_target_temp_heater_off(menuai: menuai) -> None:
    """Test if target temperature turn heater off."""
    calls = _setup_switch(menuai, True)
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_2")
async def test_temp_change_heater_on_within_tolerance(menuai: menuai) -> None:
    """Test if temperature change doesn't turn on within tolerance."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 29)
    await menuai.async_block_till_done()
    assert len(calls) == 0


@pytest.mark.usefixtures("setup_comp_2")
async def test_temp_change_heater_on_outside_tolerance(menuai: menuai) -> None:
    """Test if temperature change turn heater on outside cold tolerance."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 27)
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_2")
async def test_temp_change_heater_off_within_tolerance(menuai: menuai) -> None:
    """Test if temperature change doesn't turn off within tolerance."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 33)
    await menuai.async_block_till_done()
    assert len(calls) == 0


@pytest.mark.usefixtures("setup_comp_2")
async def test_temp_change_heater_off_outside_tolerance(menuai: menuai) -> None:
    """Test if temperature change turn heater off outside hot tolerance."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 35)
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_2")
async def test_running_when_hvac_mode_is_off(menuai: menuai) -> None:
    """Test that the switch turns off when enabled is set False."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_2")
async def test_no_state_change_when_hvac_mode_off(menuai: menuai) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 30)
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    assert len(calls) == 0


@pytest.mark.usefixtures("setup_comp_2")
async def test_hvac_mode_heat(menuai: menuai) -> None:
    """Test change mode from OFF to HEAT.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    calls = _setup_switch(menuai, False)
    await common.async_set_hvac_mode(menuai, HVACMode.HEAT)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


def _setup_switch(menuai: menuai, is_on: bool) -> list[ServiceCall]:
    """Set up the test switch."""
    menuai.states.async_set(ENT_SWITCH, STATE_ON if is_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call: ServiceCall) -> None:
        """Log service calls."""
        calls.append(call)

    menuai.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    menuai.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


@pytest.fixture
async def setup_comp_3(menuai: menuai) -> None:
    """Initialize components."""
    menuai.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "away_temp": 30,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "ac_mode": True,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_3")
async def test_set_target_temp_ac_off(menuai: menuai) -> None:
    """Test if target temperature turn ac off."""
    calls = _setup_switch(menuai, True)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 30)
    assert len(calls) == 2
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_turn_away_mode_on_cooling(menuai: menuai) -> None:
    """Test the setting away mode when cooling."""
    _setup_switch(menuai, True)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 19)
    await common.async_set_preset_mode(menuai, PRESET_AWAY)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 30


@pytest.mark.usefixtures("setup_comp_3")
async def test_hvac_mode_cool(menuai: menuai) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    await common.async_set_temperature(menuai, 25)
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    calls = _setup_switch(menuai, False)
    await common.async_set_hvac_mode(menuai, HVACMode.COOL)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_set_target_temp_ac_on(menuai: menuai) -> None:
    """Test if target temperature turn ac on."""
    calls = _setup_switch(menuai, False)
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_temp_change_ac_off_within_tolerance(menuai: menuai) -> None:
    """Test if temperature change doesn't turn ac off within tolerance."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 29.8)
    await menuai.async_block_till_done()
    assert len(calls) == 0


@pytest.mark.usefixtures("setup_comp_3")
async def test_set_temp_change_ac_off_outside_tolerance(menuai: menuai) -> None:
    """Test if temperature change turn ac off."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    _setup_sensor(menuai, 27)
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_temp_change_ac_on_within_tolerance(menuai: menuai) -> None:
    """Test if temperature change doesn't turn ac on within tolerance."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 25)
    _setup_sensor(menuai, 25.2)
    await menuai.async_block_till_done()
    assert len(calls) == 0


@pytest.mark.usefixtures("setup_comp_3")
async def test_temp_change_ac_on_outside_tolerance(menuai: menuai) -> None:
    """Test if temperature change turn ac on."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 25)
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_running_when_operating_mode_is_off_2(menuai: menuai) -> None:
    """Test that the switch turns off when enabled is set False."""
    calls = _setup_switch(menuai, True)
    await common.async_set_temperature(menuai, 30)
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_3")
async def test_no_state_change_when_operation_mode_off_2(menuai: menuai) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = _setup_switch(menuai, False)
    await common.async_set_temperature(menuai, 30)
    await common.async_set_hvac_mode(menuai, HVACMode.OFF)
    _setup_sensor(menuai, 35)
    await menuai.async_block_till_done()
    assert len(calls) == 0


async def _setup_thermostat_with_min_cycle_duration(
    menuai: menuai, ac_mode: bool, initial_hvac_mode: HVACMode
):
    """Initialize components."""
    menuai.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "ac_mode": ac_mode,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                "initial_hvac_mode": initial_hvac_mode,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    (
        "ac_mode",
        "initial_hvac_mode",
        "initial_switch_state",
        "sensor_temperature",
        "target_temperature",
    ),
    [
        (True, HVACMode.COOL, False, 30, 25),
        (True, HVACMode.COOL, True, 25, 30),
        (False, HVACMode.HEAT, True, 25, 30),
        (False, HVACMode.HEAT, False, 30, 25),
    ],
)
async def test_heating_cooling_switch_does_not_toggle_when_within_min_cycle_duration(
    menuai: menuai,
    ac_mode: bool,
    initial_hvac_mode: HVACMode,
    initial_switch_state: bool,
    sensor_temperature: int,
    target_temperature: int,
) -> None:
    """Test if heating/cooling does not toggle when inside minimum cycle."""
    # Given
    await _setup_thermostat_with_min_cycle_duration(menuai, ac_mode, initial_hvac_mode)
    calls = _setup_switch(menuai, initial_switch_state)

    # When
    await common.async_set_temperature(menuai, target_temperature)
    _setup_sensor(menuai, sensor_temperature)
    await menuai.async_block_till_done()

    # Then
    assert len(calls) == 0


@pytest.mark.parametrize(
    (
        "ac_mode",
        "initial_hvac_mode",
        "initial_switch_state",
        "sensor_temperature",
        "target_temperature",
        "expected_triggered_service_call",
    ),
    [
        (True, HVACMode.COOL, False, 30, 25, SERVICE_TURN_ON),
        (True, HVACMode.COOL, True, 25, 30, SERVICE_TURN_OFF),
        (False, HVACMode.HEAT, False, 25, 30, SERVICE_TURN_ON),
        (False, HVACMode.HEAT, True, 30, 25, SERVICE_TURN_OFF),
    ],
)
async def test_heating_cooling_switch_toggles_when_outside_min_cycle_duration(
    menuai: menuai,
    ac_mode: bool,
    initial_hvac_mode: HVACMode,
    initial_switch_state: bool,
    sensor_temperature: int,
    target_temperature: int,
    expected_triggered_service_call: str,
) -> None:
    """Test if heating/cooling toggles when outside minimum cycle."""
    # Given
    await _setup_thermostat_with_min_cycle_duration(menuai, ac_mode, initial_hvac_mode)
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = _setup_switch(menuai, initial_switch_state)

    # When
    await common.async_set_temperature(menuai, target_temperature)
    _setup_sensor(menuai, sensor_temperature)
    await menuai.async_block_till_done()

    # Then
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == expected_triggered_service_call
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.parametrize(
    (
        "ac_mode",
        "initial_hvac_mode",
        "initial_switch_state",
        "sensor_temperature",
        "target_temperature",
        "changed_hvac_mode",
        "expected_triggered_service_call",
    ),
    [
        (True, HVACMode.COOL, False, 30, 25, HVACMode.HEAT, SERVICE_TURN_ON),
        (True, HVACMode.COOL, True, 25, 30, HVACMode.OFF, SERVICE_TURN_OFF),
        (False, HVACMode.HEAT, False, 25, 30, HVACMode.HEAT, SERVICE_TURN_ON),
        (False, HVACMode.HEAT, True, 30, 25, HVACMode.OFF, SERVICE_TURN_OFF),
    ],
)
async def test_hvac_mode_change_toggles_heating_cooling_switch_even_when_within_min_cycle_duration(
    menuai: menuai,
    ac_mode: bool,
    initial_hvac_mode: HVACMode,
    initial_switch_state: bool,
    sensor_temperature: int,
    target_temperature: int,
    changed_hvac_mode: HVACMode,
    expected_triggered_service_call: str,
) -> None:
    """Test if mode change toggles heating/cooling despite minimum cycle."""
    # Given
    await _setup_thermostat_with_min_cycle_duration(menuai, ac_mode, initial_hvac_mode)
    calls = _setup_switch(menuai, initial_switch_state)

    # When
    await common.async_set_temperature(menuai, target_temperature)
    _setup_sensor(menuai, sensor_temperature)
    await menuai.async_block_till_done()

    # Then
    assert len(calls) == 0
    await common.async_set_hvac_mode(menuai, changed_hvac_mode)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "menuai"
    assert call.service == expected_triggered_service_call
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.fixture
async def setup_comp_7(menuai: menuai) -> None:
    """Initialize components."""
    menuai.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "heater": ENT_SWITCH,
                "target_temp": 25,
                "target_sensor": ENT_SENSOR,
                "ac_mode": True,
                "min_cycle_duration": datetime.timedelta(minutes=15),
                "keep_alive": datetime.timedelta(minutes=10),
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )

    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_7")
async def test_temp_change_ac_trigger_on_long_enough_3(menuai: menuai) -> None:
    """Test if turn on signal is sent at keep-alive intervals."""
    calls = _setup_switch(menuai, True)
    await menuai.async_block_till_done()
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    test_time = datetime.datetime.now(dt_util.UTC)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=10))
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_7")
async def test_temp_change_ac_trigger_off_long_enough_3(menuai: menuai) -> None:
    """Test if turn on signal is sent at keep-alive intervals."""
    calls = _setup_switch(menuai, False)
    await menuai.async_block_till_done()
    _setup_sensor(menuai, 20)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    test_time = datetime.datetime.now(dt_util.UTC)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=10))
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.fixture
async def setup_comp_8(menuai: menuai) -> None:
    """Initialize components."""
    menuai.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "target_temp": 25,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "min_cycle_duration": datetime.timedelta(minutes=15),
                "keep_alive": datetime.timedelta(minutes=10),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_8")
async def test_temp_change_heater_trigger_on_long_enough_2(menuai: menuai) -> None:
    """Test if turn on signal is sent at keep-alive intervals."""
    calls = _setup_switch(menuai, True)
    await menuai.async_block_till_done()
    _setup_sensor(menuai, 20)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    test_time = datetime.datetime.now(dt_util.UTC)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=10))
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.mark.usefixtures("setup_comp_8")
async def test_temp_change_heater_trigger_off_long_enough_2(
    menuai: menuai,
) -> None:
    """Test if turn on signal is sent at keep-alive intervals."""
    calls = _setup_switch(menuai, False)
    await menuai.async_block_till_done()
    _setup_sensor(menuai, 30)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    test_time = datetime.datetime.now(dt_util.UTC)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=5))
    await menuai.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(menuai, test_time + datetime.timedelta(minutes=10))
    await menuai.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


@pytest.fixture
async def setup_comp_9(menuai: menuai) -> None:
    """Initialize components."""
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "target_temp": 25,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "min_cycle_duration": datetime.timedelta(minutes=15),
                "keep_alive": datetime.timedelta(minutes=10),
                "precision": 0.1,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_9")
async def test_precision(menuai: menuai) -> None:
    """Test that setting precision to tenths works as intended."""
    menuai.config.units = US_CUSTOMARY_SYSTEM
    await common.async_set_temperature(menuai, 55.27)
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("temperature") == 55.3
    # check that target_temp_step defaults to precision
    assert state.attributes.get("target_temp_step") == 0.1


@pytest.fixture(
    params=[
        HVACMode.HEAT,
        HVACMode.COOL,
    ]
)
async def setup_comp_10(menuai: menuai, request: pytest.FixtureRequest) -> None:
    """Initialize components."""
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 0,
                "hot_tolerance": 0,
                "target_temp": 25,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "initial_hvac_mode": request.param,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp_10")
async def test_zero_tolerances(menuai: menuai) -> None:
    """Test that having a zero tolerance doesn't cause the switch to flip-flop."""

    # if the switch is off, it should remain off
    calls = _setup_switch(menuai, False)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    assert len(calls) == 0

    # if the switch is on, it should turn off
    calls = _setup_switch(menuai, True)
    _setup_sensor(menuai, 25)
    await menuai.async_block_till_done()
    await common.async_set_temperature(menuai, 25)
    assert len(calls) == 1


async def test_custom_setup_params(menuai: menuai) -> None:
    """Test the setup with custom parameters."""
    result = await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "min_temp": MIN_TEMP,
                "max_temp": MAX_TEMP,
                "target_temp": TARGET_TEMP,
                "target_temp_step": 0.5,
            }
        },
    )
    assert result
    await menuai.async_block_till_done()
    state = menuai.states.get(ENTITY)
    assert state.attributes.get("min_temp") == MIN_TEMP
    assert state.attributes.get("max_temp") == MAX_TEMP
    assert state.attributes.get("temperature") == TARGET_TEMP
    assert state.attributes.get("target_temp_step") == TARGET_TEMP_STEP


@pytest.mark.parametrize("hvac_mode", [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL])
async def test_restore_state(menuai: menuai, hvac_mode) -> None:
    """Ensure states are restored on startup."""
    mock_restore_cache(
        menuai,
        (
            State(
                "climate.test_thermostat",
                hvac_mode,
                {ATTR_TEMPERATURE: "20", ATTR_PRESET_MODE: PRESET_AWAY},
            ),
        ),
    )

    menuai.set_state(CoreState.starting)

    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test_thermostat",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "away_temp": 14,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AWAY
    assert state.state == hvac_mode


async def test_no_restore_state(menuai: menuai) -> None:
    """Ensure states are restored on startup if they exist.

    Allows for graceful reboot.
    """
    mock_restore_cache(
        menuai,
        (
            State(
                "climate.test_thermostat",
                HVACMode.OFF,
                {ATTR_TEMPERATURE: "20", ATTR_PRESET_MODE: PRESET_AWAY},
            ),
        ),
    )

    menuai.set_state(CoreState.starting)

    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test_thermostat",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "target_temp": 22,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 22
    assert state.state == HVACMode.OFF


async def test_initial_hvac_off_force_heater_off(menuai: menuai) -> None:
    """Ensure that restored state is coherent with real situation.

    'initial_hvac_mode: off' will force HVAC status, but we must be sure
    that heater don't keep on.
    """
    # switch is on
    calls = _setup_switch(menuai, True)
    assert menuai.states.get(ENT_SWITCH).state == STATE_ON

    _setup_sensor(menuai, 16)

    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test_thermostat",
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "target_temp": 20,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.test_thermostat")
    # 'initial_hvac_mode' will force state but must prevent heather keep working
    assert state.state == HVACMode.OFF
    # heater must be switched off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == ENT_SWITCH


async def test_restore_will_turn_off_(menuai: menuai) -> None:
    """Ensure that restored state is coherent with real situation.

    Thermostat status must trigger heater event if temp raises the target .
    """
    heater_switch = "input_boolean.test"
    mock_restore_cache(
        menuai,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT,
                {ATTR_TEMPERATURE: "18", ATTR_PRESET_MODE: PRESET_NONE},
            ),
            State(heater_switch, STATE_ON, {}),
        ),
    )

    menuai.set_state(CoreState.starting)

    assert await async_setup_component(
        menuai, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(heater_switch).state == STATE_ON

    _setup_sensor(menuai, 22)

    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": ENT_SENSOR,
                "target_temp": 20,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.HEAT
    assert menuai.states.get(heater_switch).state == STATE_ON


async def test_restore_will_turn_off_when_loaded_second(menuai: menuai) -> None:
    """Ensure that restored state is coherent with real situation.

    Switch is not available until after component is loaded
    """
    heater_switch = "input_boolean.test"
    mock_restore_cache(
        menuai,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT,
                {ATTR_TEMPERATURE: "18", ATTR_PRESET_MODE: PRESET_NONE},
            ),
            State(heater_switch, STATE_ON, {}),
        ),
    )

    menuai.set_state(CoreState.starting)

    await menuai.async_block_till_done()
    assert menuai.states.get(heater_switch) is None

    _setup_sensor(menuai, 16)

    await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": ENT_SENSOR,
                "target_temp": 20,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF

    calls_on = async_mock_service(menuai, ha.DOMAIN, SERVICE_TURN_ON)
    calls_off = async_mock_service(menuai, ha.DOMAIN, SERVICE_TURN_OFF)

    assert await async_setup_component(
        menuai, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )
    await menuai.async_block_till_done()
    # heater must be switched off
    assert len(calls_on) == 0
    assert len(calls_off) == 1
    call = calls_off[0]
    assert call.domain == menuai_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == "input_boolean.test"


async def test_restore_state_uncoherence_case(menuai: menuai) -> None:
    """Test restore from a strange state.

    - Turn the generic thermostat off
    - Restart HA and restore state from DB
    """
    _mock_restore_cache(menuai, temperature=20)

    calls = _setup_switch(menuai, False)
    _setup_sensor(menuai, 15)
    await _setup_climate(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY)
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.state == HVACMode.OFF
    assert len(calls) == 0

    calls = _setup_switch(menuai, False)
    await menuai.async_block_till_done()
    state = menuai.states.get(ENTITY)
    assert state.state == HVACMode.OFF


async def _setup_climate(menuai: menuai) -> None:
    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "away_temp": 30,
                "heater": ENT_SWITCH,
                "target_sensor": ENT_SENSOR,
                "ac_mode": True,
            }
        },
    )


def _mock_restore_cache(
    menuai: menuai, temperature: int = 20, hvac_mode: HVACMode = HVACMode.OFF
) -> None:
    mock_restore_cache(
        menuai,
        (
            State(
                ENTITY,
                hvac_mode,
                {ATTR_TEMPERATURE: str(temperature), ATTR_PRESET_MODE: PRESET_AWAY},
            ),
        ),
    )


async def test_reload(menuai: menuai) -> None:
    """Test we can reload."""

    assert await async_setup_component(
        menuai,
        CLIMATE_DOMAIN,
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "test",
                "heater": "switch.any",
                "target_sensor": "sensor.any",
            }
        },
    )

    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 1
    assert menuai.states.get("climate.test") is not None

    yaml_path = get_fixture_path("configuration.yaml", "generic_thermostat")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1
    assert menuai.states.get("climate.test") is None
    assert menuai.states.get("climate.reload")


async def test_device_id(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test for source entity device."""

    source_config_entry = MockConfigEntry()
    source_config_entry.add_to_menuai(menuai)
    source_device_entry = device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={("switch", "identifier_test")},
        connections={("mac", "30:31:32:33:34:35")},
    )
    source_entity = entity_registry.async_get_or_create(
        "switch",
        "test",
        "source",
        config_entry=source_config_entry,
        device_id=source_device_entry.id,
    )
    await menuai.async_block_till_done()
    assert entity_registry.async_get("switch.test_source") is not None

    helper_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "Test",
            "heater": "switch.test_source",
            "target_sensor": ENT_SENSOR,
            "ac_mode": False,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
        },
        title="Test",
    )
    helper_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(helper_config_entry.entry_id)
    await menuai.async_block_till_done()

    helper_entity = entity_registry.async_get("climate.test")
    assert helper_entity is not None
    assert helper_entity.device_id == source_entity.device_id
