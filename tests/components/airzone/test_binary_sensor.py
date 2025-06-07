"""The sensor tests for the Airzone platform."""

from aioairzone.const import API_ERROR_LOW_BATTERY

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from .util import async_init_integration


async def test_airzone_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of binary sensors."""

    await async_init_integration(menuai)

    # Systems
    state = menuai.states.get("binary_sensor.system_1_problem")
    assert state.state == STATE_OFF

    # Zones
    state = menuai.states.get("binary_sensor.despacho_air_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.despacho_battery")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.despacho_floor_demand")
    assert state is None

    state = menuai.states.get("binary_sensor.despacho_problem")
    assert state.state == STATE_ON
    assert state.attributes.get("errors") == [API_ERROR_LOW_BATTERY]

    state = menuai.states.get("binary_sensor.dorm_1_air_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_1_battery")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_1_floor_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_1_problem")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_2_air_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_2_battery")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_2_floor_demand")
    assert state is None

    state = menuai.states.get("binary_sensor.dorm_2_problem")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_ppal_air_demand")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.dorm_ppal_battery")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dorm_ppal_floor_demand")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.dorm_ppal_problem")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.salon_air_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.salon_battery")
    assert state is None

    state = menuai.states.get("binary_sensor.salon_floor_demand")
    assert state is None

    state = menuai.states.get("binary_sensor.salon_problem")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.airzone_2_1_battery")
    assert state is None

    state = menuai.states.get("binary_sensor.airzone_2_1_problem")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dkn_plus_battery")
    assert state is None

    state = menuai.states.get("binary_sensor.dkn_plus_problem")
    assert state.state == STATE_OFF
