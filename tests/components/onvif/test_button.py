"""Test button of ONVIF integration."""

from unittest.mock import AsyncMock

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, ButtonDeviceClass
from menuai.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import MAC, setup_onvif_integration


async def test_reboot_button(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the Reboot button."""
    await setup_onvif_integration(menuai)

    state = menuai.states.get("button.testcamera_reboot")
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_DEVICE_CLASS) == ButtonDeviceClass.RESTART

    entry = entity_registry.async_get("button.testcamera_reboot")
    assert entry
    assert entry.unique_id == f"{MAC}_reboot"


async def test_reboot_button_press(menuai: menuai) -> None:
    """Test Reboot button press."""
    _, camera, _ = await setup_onvif_integration(menuai)
    devicemgmt = await camera.create_devicemgmt_service()
    devicemgmt.SystemReboot = AsyncMock(return_value=True)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        "press",
        {ATTR_ENTITY_ID: "button.testcamera_reboot"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    devicemgmt.SystemReboot.assert_called_once()


async def test_set_dateandtime_button(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the SetDateAndTime button."""
    await setup_onvif_integration(menuai)

    state = menuai.states.get("button.testcamera_set_system_date_and_time")
    assert state
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("button.testcamera_set_system_date_and_time")
    assert entry
    assert entry.unique_id == f"{MAC}_setsystemdatetime"


async def test_set_dateandtime_button_press(menuai: menuai) -> None:
    """Test SetDateAndTime button press."""
    _, camera, device = await setup_onvif_integration(menuai)
    device.async_manually_set_date_and_time = AsyncMock(return_value=True)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        "press",
        {ATTR_ENTITY_ID: "button.testcamera_set_system_date_and_time"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    device.async_manually_set_date_and_time.assert_called_once()
