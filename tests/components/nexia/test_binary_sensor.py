"""The binary_sensor tests for the nexia platform."""

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from .util import async_init_integration


async def test_create_binary_sensors(menuai: menuai) -> None:
    """Test creation of binary sensors."""

    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.master_suite_blower_active")
    assert state.state == STATE_ON
    expected_attributes = {
        "attribution": "Data provided by Trane Technologies",
        "friendly_name": "Master Suite Blower active",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(
        state.attributes[key] == value for key, value in expected_attributes.items()
    )

    state = menuai.states.get("binary_sensor.downstairs_east_wing_blower_active")
    assert state.state == STATE_OFF
    expected_attributes = {
        "attribution": "Data provided by Trane Technologies",
        "friendly_name": "Downstairs East Wing Blower active",
    }
    # Only test for a subset of attributes in case
    # HA changes the implementation and a new one appears
    assert all(
        state.attributes[key] == value for key, value in expected_attributes.items()
    )
