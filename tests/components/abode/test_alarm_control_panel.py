"""Tests for the Abode alarm control panel device."""

from unittest.mock import PropertyMock, patch

from menuai.components.abode import ATTR_DEVICE_ID
from menuai.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    AlarmControlPanelState,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_DISARM,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform

DEVICE_ID = "alarm_control_panel.abode_alarm"


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, ALARM_DOMAIN)

    entry = entity_registry.async_get(DEVICE_ID)
    # Abode alarm device unique_id is the MAC address
    assert entry.unique_id == "001122334455"


async def test_attributes(menuai: menuai) -> None:
    """Test the alarm control panel attributes are correct."""
    await setup_platform(menuai, ALARM_DOMAIN)

    state = menuai.states.get(DEVICE_ID)
    assert state.state == AlarmControlPanelState.DISARMED
    assert state.attributes.get(ATTR_DEVICE_ID) == "area_1"
    assert not state.attributes.get("battery_backup")
    assert not state.attributes.get("cellular_backup")
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Abode Alarm"
    assert state.attributes.get(ATTR_SUPPORTED_FEATURES) == 3


async def test_set_alarm_away(menuai: menuai) -> None:
    """Test the alarm control panel can be set to away."""
    with patch(
        "jaraco.abode.event_controller.EventController.add_device_callback"
    ) as mock_callback:
        with patch("jaraco.abode.devices.alarm.Alarm.set_away") as mock_set_away:
            await setup_platform(menuai, ALARM_DOMAIN)

            await menuai.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_ARM_AWAY,
                {ATTR_ENTITY_ID: DEVICE_ID},
                blocking=True,
            )
            await menuai.async_block_till_done()
            mock_set_away.assert_called_once()

        with patch(
            "jaraco.abode.devices.alarm.Alarm.mode",
            new_callable=PropertyMock,
        ) as mock_mode:
            mock_mode.return_value = "away"

            update_callback = mock_callback.call_args[0][1]
            await menuai.async_add_executor_job(update_callback, "area_1")
            await menuai.async_block_till_done()

            state = menuai.states.get(DEVICE_ID)
            assert state.state == AlarmControlPanelState.ARMED_AWAY


async def test_set_alarm_home(menuai: menuai) -> None:
    """Test the alarm control panel can be set to home."""
    with patch(
        "jaraco.abode.event_controller.EventController.add_device_callback"
    ) as mock_callback:
        with patch("jaraco.abode.devices.alarm.Alarm.set_home") as mock_set_home:
            await setup_platform(menuai, ALARM_DOMAIN)

            await menuai.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_ARM_HOME,
                {ATTR_ENTITY_ID: DEVICE_ID},
                blocking=True,
            )
            await menuai.async_block_till_done()
            mock_set_home.assert_called_once()

        with patch(
            "jaraco.abode.devices.alarm.Alarm.mode", new_callable=PropertyMock
        ) as mock_mode:
            mock_mode.return_value = "home"

            update_callback = mock_callback.call_args[0][1]
            await menuai.async_add_executor_job(update_callback, "area_1")
            await menuai.async_block_till_done()

            state = menuai.states.get(DEVICE_ID)
            assert state.state == AlarmControlPanelState.ARMED_HOME


async def test_set_alarm_standby(menuai: menuai) -> None:
    """Test the alarm control panel can be set to standby."""
    with patch(
        "jaraco.abode.event_controller.EventController.add_device_callback"
    ) as mock_callback:
        with patch("jaraco.abode.devices.alarm.Alarm.set_standby") as mock_set_standby:
            await setup_platform(menuai, ALARM_DOMAIN)
            await menuai.services.async_call(
                ALARM_DOMAIN,
                SERVICE_ALARM_DISARM,
                {ATTR_ENTITY_ID: DEVICE_ID},
                blocking=True,
            )
            await menuai.async_block_till_done()
            mock_set_standby.assert_called_once()

        with patch(
            "jaraco.abode.devices.alarm.Alarm.mode", new_callable=PropertyMock
        ) as mock_mode:
            mock_mode.return_value = "standby"

            update_callback = mock_callback.call_args[0][1]
            await menuai.async_add_executor_job(update_callback, "area_1")
            await menuai.async_block_till_done()

            state = menuai.states.get(DEVICE_ID)
            assert state.state == AlarmControlPanelState.DISARMED


async def test_state_unknown(menuai: menuai) -> None:
    """Test an unknown alarm control panel state."""
    with patch(
        "jaraco.abode.devices.alarm.Alarm.mode", new_callable=PropertyMock
    ) as mock_mode:
        await setup_platform(menuai, ALARM_DOMAIN)
        await menuai.async_block_till_done()

        mock_mode.return_value = None

        state = menuai.states.get(DEVICE_ID)
        assert state.state == "unknown"
