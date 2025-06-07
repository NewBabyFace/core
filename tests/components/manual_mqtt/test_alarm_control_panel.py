"""The tests for the manual_mqtt Alarm Control Panel component."""

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from menuai.components import alarm_control_panel
from menuai.components.alarm_control_panel import AlarmControlPanelState
from menuai.const import (
    ATTR_CODE,
    ATTR_ENTITY_ID,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_CUSTOM_BYPASS,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_ARM_NIGHT,
    SERVICE_ALARM_ARM_VACATION,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    assert_setup_component,
    async_fire_mqtt_message,
    async_fire_time_changed,
)
from tests.components.alarm_control_panel import common
from tests.typing import MqttMockHAClient

CODE = "HELLO_CODE"


async def test_fail_setup_without_state_topic(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test for failing with no state topic."""
    with assert_setup_component(0, alarm_control_panel.DOMAIN) as config:
        assert await async_setup_component(
            menuai,
            alarm_control_panel.DOMAIN,
            {
                alarm_control_panel.DOMAIN: {
                    "platform": "mqtt_alarm",
                    "command_topic": "alarm/command",
                }
            },
        )
        assert not config[alarm_control_panel.DOMAIN]


async def test_fail_setup_without_command_topic(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test failing with no command topic."""
    with assert_setup_component(0, alarm_control_panel.DOMAIN):
        assert await async_setup_component(
            menuai,
            alarm_control_panel.DOMAIN,
            {
                alarm_control_panel.DOMAIN: {
                    "platform": "mqtt_alarm",
                    "state_topic": "alarm/state",
                }
            },
        )


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_no_pending(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test arm method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: CODE},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == expected_state


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_no_pending_when_code_not_req(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test arm method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "code_arm_required": False,
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: CODE},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == expected_state


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_with_pending(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test arm method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "pending_time": 1,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: CODE},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    state = menuai.states.get(entity_id)
    assert state.attributes["post_pending_state"] == expected_state

    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == expected_state

    # Do not go to the pending state when updating to the same state
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: CODE},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == expected_state


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_with_invalid_code(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Attempt to arm without a valid code."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "pending_time": 1,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    with pytest.raises(menuaiError, match=r"^Invalid alarm code provided$"):
        await menuai.services.async_call(
            alarm_control_panel.DOMAIN,
            service,
            {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: f"{CODE}2"},
            blocking=True,
        )

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_with_template_code(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Attempt to arm with a template-based code."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code_template": '{{ "abc" }}',
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "abc"},
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state.state == expected_state


@pytest.mark.parametrize(
    ("service", "expected_state"),
    [
        (SERVICE_ALARM_ARM_AWAY, AlarmControlPanelState.ARMED_AWAY),
        (
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        ),
        (SERVICE_ALARM_ARM_HOME, AlarmControlPanelState.ARMED_HOME),
        (SERVICE_ALARM_ARM_NIGHT, AlarmControlPanelState.ARMED_NIGHT),
        (SERVICE_ALARM_ARM_VACATION, AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_with_specific_pending(
    menuai: menuai,
    service,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test arm method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 10,
                expected_state: {"pending_time": 2},
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "1234"},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    future = dt_util.utcnow() + timedelta(seconds=2)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == expected_state


async def test_trigger_no_pending(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test triggering when no pending submitted method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 1,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai, entity_id=entity_id)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    future = dt_util.utcnow() + timedelta(seconds=60)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_delay(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method and switch from pending to triggered."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "delay_time": 1,
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_trigger_zero_trigger_time(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disabled trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 0,
                "trigger_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_zero_trigger_time_with_pending(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disabled trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 2,
                "trigger_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_pending(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test arm home method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 2,
                "trigger_time": 3,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    state = menuai.states.get(entity_id)
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=2)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_disarm_after_trigger(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarm after trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "pending_time": 0,
                "disarm_after_trigger": True,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_zero_specific_trigger_time(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "disarmed": {"trigger_time": 0},
                "pending_time": 0,
                "disarm_after_trigger": True,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_unused_zero_specific_trigger_time(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarm after trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "armed_home": {"trigger_time": 0},
                "pending_time": 0,
                "disarm_after_trigger": True,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_specific_trigger_time(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarm after trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "disarmed": {"trigger_time": 5},
                "pending_time": 0,
                "disarm_after_trigger": True,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_back_to_back_trigger_with_no_disarm_after_trigger(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test no disarm after back to back trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE, entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY


async def test_disarm_while_pending_trigger(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarming while pending state."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    await common.async_alarm_disarm(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_disarm_during_trigger_with_invalid_code(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarming while code is invalid."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 5,
                "code": "12345",
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED
    assert (
        menuai.states.get(entity_id).attributes[alarm_control_panel.ATTR_CODE_FORMAT]
        == alarm_control_panel.CodeFormat.NUMBER
    )

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    with pytest.raises(menuaiError, match=r"Invalid alarm code provided$"):
        await common.async_alarm_disarm(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_unused_specific_delay(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method and switch from pending to triggered."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "delay_time": 5,
                "pending_time": 0,
                "armed_home": {"delay_time": 10},
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_specific_delay(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method and switch from pending to triggered."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "delay_time": 10,
                "pending_time": 0,
                "armed_away": {"delay_time": 1},
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_pending_and_delay(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method and switch from pending to triggered."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "delay_time": 1,
                "pending_time": 0,
                "triggered": {"pending_time": 1},
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future += timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_pending_and_specific_delay(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test trigger method and switch from pending to triggered."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "delay_time": 10,
                "pending_time": 0,
                "armed_away": {"delay_time": 1},
                "triggered": {"pending_time": 1},
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED

    future += timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_trigger_with_specific_pending(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test arm home method."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 10,
                "triggered": {"pending_time": 2},
                "trigger_time": 3,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    await common.async_alarm_trigger(menuai)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    future = dt_util.utcnow() + timedelta(seconds=2)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_trigger_with_no_disarm_after_trigger(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarm after trigger."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "trigger_time": 5,
                "pending_time": 0,
                "delay_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE, entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    future = dt_util.utcnow() + timedelta(seconds=5)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY


async def test_arm_away_after_disabled_disarmed(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test pending state with and without zero trigger time."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code": CODE,
                "pending_time": 0,
                "delay_time": 1,
                "armed_away": {"pending_time": 1},
                "disarmed": {"trigger_time": 0},
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_away(menuai, CODE)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["pre_pending_state"] == AlarmControlPanelState.DISARMED
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.ARMED_AWAY

    await common.async_alarm_trigger(menuai, entity_id=entity_id)

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.PENDING
    assert state.attributes["pre_pending_state"] == AlarmControlPanelState.DISARMED
    assert state.attributes["post_pending_state"] == AlarmControlPanelState.ARMED_AWAY

    future = dt_util.utcnow() + timedelta(seconds=1)
    with freeze_time(future):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

        state = menuai.states.get(entity_id)
        assert state.state == AlarmControlPanelState.ARMED_AWAY

        await common.async_alarm_trigger(menuai, entity_id=entity_id)

        state = menuai.states.get(entity_id)
        assert state.state == AlarmControlPanelState.PENDING
        assert (
            state.attributes["pre_pending_state"] == AlarmControlPanelState.ARMED_AWAY
        )
        assert (
            state.attributes["post_pending_state"] == AlarmControlPanelState.TRIGGERED
        )

    future += timedelta(seconds=1)
    with freeze_time(future):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.TRIGGERED


async def test_disarm_with_template_code(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Attempt to disarm with a valid or invalid template-based code."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            "alarm_control_panel": {
                "platform": "manual_mqtt",
                "name": "test",
                "code_template": '{{ "" if from_state == "disarmed" else "abc" }}',
                "pending_time": 0,
                "disarm_after_trigger": False,
                "command_topic": "alarm/command",
                "state_topic": "alarm/state",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_arm_home(menuai, "def")

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.ARMED_HOME

    with pytest.raises(menuaiError, match=r"Invalid alarm code provided$"):
        await common.async_alarm_disarm(menuai, "def")

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.ARMED_HOME

    await common.async_alarm_disarm(menuai, "abc")

    state = menuai.states.get(entity_id)
    assert state.state == AlarmControlPanelState.DISARMED


@pytest.mark.parametrize(
    ("config", "expected_state"),
    [
        ("payload_arm_away", AlarmControlPanelState.ARMED_AWAY),
        ("payload_arm_custom_bypass", AlarmControlPanelState.ARMED_CUSTOM_BYPASS),
        ("payload_arm_home", AlarmControlPanelState.ARMED_HOME),
        ("payload_arm_night", AlarmControlPanelState.ARMED_NIGHT),
        ("payload_arm_vacation", AlarmControlPanelState.ARMED_VACATION),
    ],
)
async def test_arm_via_command_topic(
    menuai: menuai,
    config,
    expected_state,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test arming via command topic."""
    command = config[8:].upper()
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            alarm_control_panel.DOMAIN: {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 1,
                "state_topic": "alarm/state",
                "command_topic": "alarm/command",
                config: command,
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    # Fire the arm command via MQTT; ensure state changes to arming
    async_fire_mqtt_message(menuai, "alarm/command", command)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    # Fast-forward a little bit
    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == expected_state


async def test_disarm_pending_via_command_topic(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test disarming pending alarm via command topic."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            alarm_control_panel.DOMAIN: {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 1,
                "state_topic": "alarm/state",
                "command_topic": "alarm/command",
                "payload_disarm": "DISARM",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    await common.async_alarm_trigger(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.PENDING

    # Now that we're pending, receive a command to disarm
    async_fire_mqtt_message(menuai, "alarm/command", "DISARM")
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_state_changes_are_published_to_mqtt(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test publishing of MQTT messages when state changes."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            alarm_control_panel.DOMAIN: {
                "platform": "manual_mqtt",
                "name": "test",
                "pending_time": 1,
                "trigger_time": 1,
                "state_topic": "alarm/state",
                "command_topic": "alarm/command",
            }
        },
    )
    await menuai.async_block_till_done()

    # Component should send disarmed alarm state on startup
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.DISARMED, 0, True
    )
    mqtt_mock.async_publish.reset_mock()

    # Arm in home mode
    await common.async_alarm_arm_home(menuai, "1234")
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.PENDING, 0, True
    )
    mqtt_mock.async_publish.reset_mock()
    # Fast-forward a little bit
    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.ARMED_HOME, 0, True
    )
    mqtt_mock.async_publish.reset_mock()

    # Arm in away mode
    await common.async_alarm_arm_away(menuai, "1234")
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.PENDING, 0, True
    )
    mqtt_mock.async_publish.reset_mock()
    # Fast-forward a little bit
    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.ARMED_AWAY, 0, True
    )
    mqtt_mock.async_publish.reset_mock()

    # Arm in night mode
    await common.async_alarm_arm_night(menuai, "1234")
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.PENDING, 0, True
    )
    mqtt_mock.async_publish.reset_mock()
    # Fast-forward a little bit
    future = dt_util.utcnow() + timedelta(seconds=1)
    with patch(
        ("menuai.components.manual_mqtt.alarm_control_panel.dt_util.utcnow"),
        return_value=future,
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.ARMED_NIGHT, 0, True
    )
    mqtt_mock.async_publish.reset_mock()

    # Disarm
    await common.async_alarm_disarm(menuai)
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/state", AlarmControlPanelState.DISARMED, 0, True
    )


async def test_no_mqtt(menuai: menuai, caplog: pytest.LogCaptureFixture) -> None:
    """Test publishing of MQTT messages when state changes."""
    assert await async_setup_component(
        menuai,
        alarm_control_panel.DOMAIN,
        {
            alarm_control_panel.DOMAIN: {
                "platform": "manual_mqtt",
                "name": "test",
                "state_topic": "alarm/state",
                "command_topic": "alarm/command",
            }
        },
    )
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"
    assert menuai.states.get(entity_id) is None
    assert "MQTT integration is not available" in caplog.text
