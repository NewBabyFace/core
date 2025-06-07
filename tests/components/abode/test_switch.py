"""Tests for the Abode switch device."""

from unittest.mock import patch

from menuai.components.abode.const import DOMAIN
from menuai.components.abode.services import SERVICE_TRIGGER_AUTOMATION
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform

AUTOMATION_ID = "switch.test_automation"
AUTOMATION_UID = "47fae27488f74f55b964a81a066c3a01"
DEVICE_ID = "switch.test_switch"
DEVICE_UID = "0012a4d3614cb7e2b8c9abea31d2fb2a"


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    entry = entity_registry.async_get(AUTOMATION_ID)
    assert entry.unique_id == AUTOMATION_UID

    entry = entity_registry.async_get(DEVICE_ID)
    assert entry.unique_id == DEVICE_UID


async def test_attributes(menuai: menuai) -> None:
    """Test the switch attributes are correct."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    state = menuai.states.get(DEVICE_ID)
    assert state.state == STATE_OFF


async def test_switch_on(menuai: menuai) -> None:
    """Test the switch can be turned on."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    with patch("jaraco.abode.devices.switch.Switch.switch_on") as mock_switch_on:
        await menuai.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await menuai.async_block_till_done()

        mock_switch_on.assert_called_once()


async def test_switch_off(menuai: menuai) -> None:
    """Test the switch can be turned off."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    with patch("jaraco.abode.devices.switch.Switch.switch_off") as mock_switch_off:
        await menuai.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await menuai.async_block_till_done()

        mock_switch_off.assert_called_once()


async def test_automation_attributes(menuai: menuai) -> None:
    """Test the automation attributes are correct."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    state = menuai.states.get(AUTOMATION_ID)
    # State is set based on "enabled" key in automation JSON.
    assert state.state == STATE_ON


async def test_turn_automation_off(menuai: menuai) -> None:
    """Test the automation can be turned off."""
    with patch("jaraco.abode.automation.Automation.enable") as mock_trigger:
        await setup_platform(menuai, SWITCH_DOMAIN)

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()

        mock_trigger.assert_called_once_with(False)


async def test_turn_automation_on(menuai: menuai) -> None:
    """Test the automation can be turned on."""
    with patch("jaraco.abode.automation.Automation.enable") as mock_trigger:
        await setup_platform(menuai, SWITCH_DOMAIN)

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()

        mock_trigger.assert_called_once_with(True)


async def test_trigger_automation(menuai: menuai) -> None:
    """Test the trigger automation service."""
    await setup_platform(menuai, SWITCH_DOMAIN)

    with patch("jaraco.abode.automation.Automation.trigger") as mock:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_TRIGGER_AUTOMATION,
            {ATTR_ENTITY_ID: AUTOMATION_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()

        mock.assert_called_once()
