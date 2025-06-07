"""Test switch platform of ONVIF integration."""

from unittest.mock import AsyncMock

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import MAC, Capabilities, setup_onvif_integration


async def test_wiper_switch(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the Wiper switch."""
    _config, _camera, device = await setup_onvif_integration(menuai)
    device.profiles = device.async_get_profiles()

    state = menuai.states.get("switch.testcamera_wiper")
    assert state
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("switch.testcamera_wiper")
    assert entry
    assert entry.unique_id == f"{MAC}_wiper"


async def test_wiper_switch_no_ptz(menuai: menuai) -> None:
    """Test the wiper switch does not get created if the camera does not support ptz."""
    _config, _camera, device = await setup_onvif_integration(
        menuai, capabilities=Capabilities(imaging=True, ptz=False)
    )
    device.profiles = device.async_get_profiles()

    assert menuai.states.get("switch.testcamera_wiper") is None


async def test_turn_wiper_switch_on(menuai: menuai) -> None:
    """Test Wiper switch turn on."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_run_aux_command = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: "switch.testcamera_wiper"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_run_aux_command.assert_called_once()
    state = menuai.states.get("switch.testcamera_wiper")
    assert state.state == STATE_ON


async def test_turn_wiper_switch_off(menuai: menuai) -> None:
    """Test Wiper switch turn off."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_run_aux_command = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {ATTR_ENTITY_ID: "switch.testcamera_wiper"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_run_aux_command.assert_called_once()
    state = menuai.states.get("switch.testcamera_wiper")
    assert state.state == STATE_OFF


async def test_autofocus_switch(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the autofocus switch."""
    _config, _camera, device = await setup_onvif_integration(menuai)
    device.profiles = device.async_get_profiles()

    state = menuai.states.get("switch.testcamera_autofocus")
    assert state
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("switch.testcamera_autofocus")
    assert entry
    assert entry.unique_id == f"{MAC}_autofocus"


async def test_auto_focus_switch_no_imaging(menuai: menuai) -> None:
    """Test the autofocus switch does not get created if the camera does not support imaging."""
    _config, _camera, device = await setup_onvif_integration(
        menuai, capabilities=Capabilities(imaging=False, ptz=True)
    )
    device.profiles = device.async_get_profiles()

    assert menuai.states.get("switch.testcamera_autofocus") is None


async def test_turn_autofocus_switch_on(menuai: menuai) -> None:
    """Test autofocus switch turn on."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_set_imaging_settings = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: "switch.testcamera_autofocus"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_set_imaging_settings.assert_called_once()
    state = menuai.states.get("switch.testcamera_autofocus")
    assert state.state == STATE_ON


async def test_turn_autofocus_switch_off(menuai: menuai) -> None:
    """Test autofocus switch turn off."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_set_imaging_settings = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {ATTR_ENTITY_ID: "switch.testcamera_autofocus"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_set_imaging_settings.assert_called_once()
    state = menuai.states.get("switch.testcamera_autofocus")
    assert state.state == STATE_OFF


async def test_infrared_switch(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the autofocus switch."""
    _config, _camera, device = await setup_onvif_integration(menuai)
    device.profiles = device.async_get_profiles()

    state = menuai.states.get("switch.testcamera_ir_lamp")
    assert state
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("switch.testcamera_ir_lamp")
    assert entry
    assert entry.unique_id == f"{MAC}_ir_lamp"


async def test_infrared_switch_no_imaging(menuai: menuai) -> None:
    """Test the infrared switch does not get created if the camera does not support imaging."""
    _config, _camera, device = await setup_onvif_integration(
        menuai, capabilities=Capabilities(imaging=False, ptz=False)
    )
    device.profiles = device.async_get_profiles()

    assert menuai.states.get("switch.testcamera_ir_lamp") is None


async def test_turn_infrared_switch_on(menuai: menuai) -> None:
    """Test infrared switch turn on."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_set_imaging_settings = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: "switch.testcamera_ir_lamp"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_set_imaging_settings.assert_called_once()
    state = menuai.states.get("switch.testcamera_ir_lamp")
    assert state.state == STATE_ON


async def test_turn_infrared_switch_off(menuai: menuai) -> None:
    """Test infrared switch turn off."""
    _, _camera, device = await setup_onvif_integration(menuai)
    device.async_set_imaging_settings = AsyncMock(return_value=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {ATTR_ENTITY_ID: "switch.testcamera_ir_lamp"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_set_imaging_settings.assert_called_once()
    state = menuai.states.get("switch.testcamera_ir_lamp")
    assert state.state == STATE_OFF
