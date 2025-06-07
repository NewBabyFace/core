"""The sensor tests for the tado platform."""

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from .util import async_init_integration


async def test_air_con_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of aircon sensors."""

    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.air_conditioning_power")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.air_conditioning_connectivity")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.air_conditioning_overlay")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.air_conditioning_window")
    assert state.state == STATE_OFF


async def test_heater_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of heater sensors."""

    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.baseboard_heater_power")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.baseboard_heater_connectivity")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.baseboard_heater_early_start")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.baseboard_heater_overlay")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.baseboard_heater_window")
    assert state.state == STATE_OFF


async def test_water_heater_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of water heater sensors."""

    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.water_heater_connectivity")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.water_heater_overlay")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.water_heater_power")
    assert state.state == STATE_ON


async def test_home_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of home binary sensors."""

    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.wr1_connection_state")
    assert state.state == STATE_ON
