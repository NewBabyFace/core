"""Tests for light platform."""

from pywizlight import PilotBuilder

from menuai.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    DOMAIN as LIGHT_DOMAIN,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import (
    FAKE_MAC,
    FAKE_OLD_FIRMWARE_DIMMABLE_BULB,
    FAKE_RGBW_BULB,
    FAKE_RGBWW_BULB,
    FAKE_TURNABLE_BULB,
    async_push_update,
    async_setup_integration,
)


async def test_light_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a light unique id."""
    await async_setup_integration(menuai)
    entity_id = "light.mock_title"
    assert entity_registry.async_get(entity_id).unique_id == FAKE_MAC
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON


async def test_light_operation(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a light operation."""
    bulb, _ = await async_setup_integration(menuai)
    entity_id = "light.mock_title"
    assert entity_registry.async_get(entity_id).unique_id == FAKE_MAC
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.turn_off.assert_called_once()

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, "state": False})
    assert menuai.states.get(entity_id).state == STATE_OFF

    await menuai.services.async_call(
        LIGHT_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    bulb.turn_on.assert_called_once()

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, "state": True})
    assert menuai.states.get(entity_id).state == STATE_ON


async def test_rgbww_light(menuai: menuai) -> None:
    """Test a light operation with a rgbww light."""
    bulb, _ = await async_setup_integration(menuai, bulb_type=FAKE_RGBWW_BULB)
    entity_id = "light.mock_title"
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_RGBWW_COLOR: (1, 2, 3, 4, 5)},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"b": 3, "c": 4, "g": 2, "r": 1, "state": True, "w": 5}

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_RGBWW_COLOR] == (1, 2, 3, 4, 5)

    bulb.turn_on.reset_mock()
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_COLOR_TEMP_KELVIN: 6535, ATTR_BRIGHTNESS: 128},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"dimming": 50, "temp": 6535, "state": True}
    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == 6535

    bulb.turn_on.reset_mock()
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: "Ocean"},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"sceneId": 1, "state": True}
    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_EFFECT] == "Ocean"

    bulb.turn_on.reset_mock()
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: "Rhythm"},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"state": True}


async def test_rgbw_light(menuai: menuai) -> None:
    """Test a light operation with a rgbww light."""
    bulb, _ = await async_setup_integration(menuai, bulb_type=FAKE_RGBW_BULB)
    entity_id = "light.mock_title"
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_RGBW_COLOR: (1, 2, 3, 4)},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"b": 3, "g": 2, "r": 1, "state": True, "w": 4}

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_RGBW_COLOR] == (1, 2, 3, 4)

    bulb.turn_on.reset_mock()
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_COLOR_TEMP_KELVIN: 6535, ATTR_BRIGHTNESS: 128},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"dimming": 50, "temp": 6535, "state": True}


async def test_turnable_light(menuai: menuai) -> None:
    """Test a light operation with a turnable light."""
    bulb, _ = await async_setup_integration(menuai, bulb_type=FAKE_TURNABLE_BULB)
    entity_id = "light.mock_title"
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_COLOR_TEMP_KELVIN: 6535, ATTR_BRIGHTNESS: 128},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"dimming": 50, "temp": 6535, "state": True}

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_COLOR_TEMP_KELVIN] == 6535


async def test_old_firmware_dimmable_light(menuai: menuai) -> None:
    """Test a light operation with a dimmable light with old firmware."""
    bulb, _ = await async_setup_integration(
        menuai, bulb_type=FAKE_OLD_FIRMWARE_DIMMABLE_BULB
    )
    entity_id = "light.mock_title"
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 128},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"dimming": 50, "state": True}

    await async_push_update(menuai, bulb, {"mac": FAKE_MAC, **pilot.pilot_params})
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 128

    bulb.turn_on.reset_mock()
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 255},
        blocking=True,
    )
    pilot: PilotBuilder = bulb.turn_on.mock_calls[0][1][0]
    assert pilot.pilot_params == {"dimming": 100, "state": True}
