"""Tests for HomematicIP Cloud alarm control panel."""

from homematicip.async_home import AsyncHome

from menuai.components.alarm_control_panel import AlarmControlPanelState
from menuai.core import menuai

from .helper import HomeFactory, get_and_check_entity_basics


async def _async_manipulate_security_zones(
    menuai: menuai,
    home: AsyncHome,
    internal_active: bool = False,
    external_active: bool = False,
    alarm_triggered: bool = False,
) -> None:
    """Set new values on hmip security zones."""
    json = home._rawJSONData
    json["functionalHomes"]["SECURITY_AND_ALARM"]["alarmActive"] = alarm_triggered
    external_zone_id = json["functionalHomes"]["SECURITY_AND_ALARM"]["securityZones"][
        "EXTERNAL"
    ]
    internal_zone_id = json["functionalHomes"]["SECURITY_AND_ALARM"]["securityZones"][
        "INTERNAL"
    ]
    external_zone = home.search_group_by_id(external_zone_id)
    external_zone.active = external_active
    internal_zone = home.search_group_by_id(internal_zone_id)
    internal_zone.active = internal_active

    home.update_home_only(json)
    home.fire_update_event(json)
    await menuai.async_block_till_done()


async def test_hmip_alarm_control_panel(
    menuai: menuai, default_mock_hap_factory: HomeFactory
) -> None:
    """Test HomematicipAlarmControlPanel."""
    entity_id = "alarm_control_panel.hmip_alarm_control_panel"
    entity_name = "HmIP Alarm Control Panel"
    device_model = None
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_groups=["EXTERNAL", "INTERNAL"]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        menuai, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "disarmed"
    assert not hmip_device

    home = mock_hap.home

    await menuai.services.async_call(
        "alarm_control_panel", "alarm_arm_away", {"entity_id": entity_id}, blocking=True
    )
    assert home.mock_calls[-1][0] == "set_security_zones_activation_async"
    assert home.mock_calls[-1][1] == (True, True)
    await _async_manipulate_security_zones(
        menuai, home, internal_active=True, external_active=True
    )
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await menuai.services.async_call(
        "alarm_control_panel", "alarm_arm_home", {"entity_id": entity_id}, blocking=True
    )
    assert home.mock_calls[-1][0] == "set_security_zones_activation_async"
    assert home.mock_calls[-1][1] == (False, True)
    await _async_manipulate_security_zones(menuai, home, external_active=True)
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_HOME

    await menuai.services.async_call(
        "alarm_control_panel", "alarm_disarm", {"entity_id": entity_id}, blocking=True
    )
    assert home.mock_calls[-1][0] == "set_security_zones_activation_async"
    assert home.mock_calls[-1][1] == (False, False)
    await _async_manipulate_security_zones(menuai, home)
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await menuai.services.async_call(
        "alarm_control_panel", "alarm_arm_away", {"entity_id": entity_id}, blocking=True
    )
    assert home.mock_calls[-1][0] == "set_security_zones_activation_async"
    assert home.mock_calls[-1][1] == (True, True)
    await _async_manipulate_security_zones(
        menuai, home, internal_active=True, external_active=True, alarm_triggered=True
    )
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    await menuai.services.async_call(
        "alarm_control_panel", "alarm_arm_home", {"entity_id": entity_id}, blocking=True
    )
    assert home.mock_calls[-1][0] == "set_security_zones_activation_async"
    assert home.mock_calls[-1][1] == (False, True)
    await _async_manipulate_security_zones(
        menuai, home, external_active=True, alarm_triggered=True
    )
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED
