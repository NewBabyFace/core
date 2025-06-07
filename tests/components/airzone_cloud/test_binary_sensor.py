"""The binary sensor tests for the Airzone Cloud platform."""

from aioairzone_cloud.const import API_OLD_ID

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from .util import async_init_integration


async def test_airzone_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of binary sensors."""

    await async_init_integration(menuai)

    # Aidoo
    state = menuai.states.get("binary_sensor.bron_problem")
    assert state.state == STATE_OFF
    assert state.attributes.get("errors") is None
    assert state.attributes.get("warnings") is None

    state = menuai.states.get("binary_sensor.bron_running")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.bron_pro_problem")
    assert state.state == STATE_OFF
    assert state.attributes.get("errors") is None
    assert state.attributes.get("warnings") is None

    state = menuai.states.get("binary_sensor.bron_pro_running")
    assert state.state == STATE_ON

    # Systems
    state = menuai.states.get("binary_sensor.system_1_problem")
    assert state.state == STATE_ON
    assert state.attributes.get("errors") == [
        {
            API_OLD_ID: "error-id",
        },
    ]
    assert state.attributes.get("warnings") is None

    # Zones
    state = menuai.states.get("binary_sensor.dormitorio_air_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dormitorio_air_quality_active")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dormitorio_battery")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dormitorio_floor_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.dormitorio_problem")
    assert state.state == STATE_OFF
    assert state.attributes.get("warnings") is None

    state = menuai.states.get("binary_sensor.dormitorio_running")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.salon_air_demand")
    assert state.state == STATE_ON

    state = menuai.states.get("binary_sensor.salon_air_quality_active")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.salon_floor_demand")
    assert state.state == STATE_OFF

    state = menuai.states.get("binary_sensor.salon_problem")
    assert state.state == STATE_OFF
    assert state.attributes.get("warnings") is None

    state = menuai.states.get("binary_sensor.salon_running")
    assert state.state == STATE_ON
