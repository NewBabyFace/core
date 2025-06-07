"""The tests the MQTT alarm control panel component."""

from contextlib import AbstractContextManager, contextmanager
import copy
import json
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import alarm_control_panel, mqtt
from menuai.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from menuai.components.mqtt.alarm_control_panel import (
    MQTT_ALARM_ATTRIBUTES_BLOCKED,
)
from menuai.components.mqtt.models import PublishPayloadType
from menuai.const import (
    ATTR_CODE,
    ATTR_ENTITY_ID,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_CUSTOM_BYPASS,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_ARM_NIGHT,
    SERVICE_ALARM_ARM_VACATION,
    SERVICE_ALARM_DISARM,
    SERVICE_ALARM_TRIGGER,
    SERVICE_RELOAD,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError

from .common import (
    help_custom_config,
    help_test_availability_when_connection_lost,
    help_test_availability_without_topic,
    help_test_custom_availability_payload,
    help_test_default_availability_payload,
    help_test_discovery_broken,
    help_test_discovery_removal,
    help_test_discovery_update,
    help_test_discovery_update_attr,
    help_test_discovery_update_unchanged,
    help_test_encoding_subscribable_topics,
    help_test_entity_debug_info_message,
    help_test_entity_device_info_remove,
    help_test_entity_device_info_update,
    help_test_entity_device_info_with_connection,
    help_test_entity_device_info_with_identifier,
    help_test_entity_icon_and_entity_picture,
    help_test_entity_id_update_discovery_update,
    help_test_entity_id_update_subscriptions,
    help_test_entity_name,
    help_test_publishing_with_custom_encoding,
    help_test_reloadable,
    help_test_setting_attribute_via_mqtt_json_message,
    help_test_setting_attribute_with_template,
    help_test_setting_blocked_attribute_via_mqtt_json_message,
    help_test_skipped_async_ha_write_state,
    help_test_unique_id,
    help_test_unload_config_entry_with_platform,
    help_test_update_with_json_attrs_bad_json,
    help_test_update_with_json_attrs_not_dict,
)

from tests.common import async_fire_mqtt_message
from tests.components.alarm_control_panel import common
from tests.typing import MqttMockHAClientGenerator, MqttMockPahoClient

CODE_NUMBER = "1234"
CODE_TEXT = "HELLO_CODE"

DEFAULT_FEATURES = (
    AlarmControlPanelEntityFeature.ARM_HOME
    | AlarmControlPanelEntityFeature.ARM_AWAY
    | AlarmControlPanelEntityFeature.ARM_NIGHT
    | AlarmControlPanelEntityFeature.ARM_VACATION
    | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
    | AlarmControlPanelEntityFeature.TRIGGER
)

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {
        alarm_control_panel.DOMAIN: {
            "name": "test",
            "state_topic": "alarm/state",
            "command_topic": "alarm/command",
        }
    }
}

DEFAULT_CONFIG_CODE_NOT_REQUIRED = {
    mqtt.DOMAIN: {
        alarm_control_panel.DOMAIN: {
            "name": "test",
            "state_topic": "alarm/state",
            "command_topic": "alarm/command",
            "code_arm_required": False,
        }
    }
}

DEFAULT_CONFIG_CODE = {
    mqtt.DOMAIN: {
        alarm_control_panel.DOMAIN: {
            "name": "test",
            "state_topic": "alarm/state",
            "command_topic": "alarm/command",
            "code": "0123",
            "code_arm_required": True,
        }
    }
}

DEFAULT_CONFIG_REMOTE_CODE = {
    mqtt.DOMAIN: {
        alarm_control_panel.DOMAIN: {
            "name": "test",
            "state_topic": "alarm/state",
            "command_topic": "alarm/command",
            "code": "REMOTE_CODE",
            "code_arm_required": True,
        }
    }
}

DEFAULT_CONFIG_REMOTE_CODE_TEXT = {
    mqtt.DOMAIN: {
        alarm_control_panel.DOMAIN: {
            "name": "test",
            "state_topic": "alarm/state",
            "command_topic": "alarm/command",
            "code": "REMOTE_CODE_TEXT",
            "code_arm_required": True,
        }
    }
}


@contextmanager
def does_not_raise():
    """Do not raise error."""
    yield


@pytest.mark.parametrize(
    ("menuai_config", "valid"),
    [
        (
            {
                mqtt.DOMAIN: {
                    alarm_control_panel.DOMAIN: {
                        "name": "test",
                        "command_topic": "alarm/command",
                    }
                }
            },
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    alarm_control_panel.DOMAIN: {
                        "name": "test",
                        "state_topic": "alarm/state",
                    }
                }
            },
            False,
        ),
        (
            {
                mqtt.DOMAIN: {
                    alarm_control_panel.DOMAIN: {
                        "name": "test",
                        "command_topic": "alarm/command",
                        "state_topic": "alarm/state",
                    }
                }
            },
            True,
        ),
    ],
)
async def test_fail_setup_without_state_or_command_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, valid: bool
) -> None:
    """Test for failing setup with no state or command topic."""
    assert await mqtt_mock_entry()
    state = menuai.states.get(f"{alarm_control_panel.DOMAIN}.test")
    assert (state is not None) == valid


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_update_state_via_state_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test updating with via state topic."""
    await mqtt_mock_entry()
    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == STATE_UNKNOWN

    for state in (
        AlarmControlPanelState.DISARMED,
        AlarmControlPanelState.ARMED_HOME,
        AlarmControlPanelState.ARMED_AWAY,
        AlarmControlPanelState.ARMED_NIGHT,
        AlarmControlPanelState.ARMED_VACATION,
        AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
        AlarmControlPanelState.PENDING,
        AlarmControlPanelState.ARMING,
        AlarmControlPanelState.DISARMING,
        AlarmControlPanelState.TRIGGERED,
    ):
        async_fire_mqtt_message(menuai, "alarm/state", state)
        assert menuai.states.get(entity_id).state == state

    # Ignore empty payload (last state is AlarmControlPanelState.TRIGGERED)
    async_fire_mqtt_message(menuai, "alarm/state", "")
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.TRIGGERED

    # Reset state on `None` payload
    async_fire_mqtt_message(menuai, "alarm/state", "None")
    assert menuai.states.get(entity_id).state == STATE_UNKNOWN


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_ignore_update_state_if_unknown_via_state_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test ignoring updates via state topic."""
    await mqtt_mock_entry()

    entity_id = "alarm_control_panel.test"

    assert menuai.states.get(entity_id).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "alarm/state", "unsupported state")
    assert menuai.states.get(entity_id).state == STATE_UNKNOWN


@pytest.mark.parametrize(
    ("menuai_config", "expected_features", "valid"),
    [
        (
            DEFAULT_CONFIG,
            DEFAULT_FEATURES,
            True,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": []},),
            ),
            AlarmControlPanelEntityFeature(0),
            True,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": ["arm_home"]},),
            ),
            AlarmControlPanelEntityFeature.ARM_HOME,
            True,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": ["arm_home", "arm_away"]},),
            ),
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY,
            True,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": "invalid"},),
            ),
            None,
            False,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": ["invalid"]},),
            ),
            None,
            False,
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG,
                ({"supported_features": ["arm_home", "invalid"]},),
            ),
            None,
            False,
        ),
    ],
)
async def test_supported_features(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    expected_features: AlarmControlPanelEntityFeature | None,
    valid: bool,
) -> None:
    """Test conditional enablement of supported features."""
    assert await mqtt_mock_entry()
    state = menuai.states.get("alarm_control_panel.test")
    if valid:
        assert state is not None
        assert state.attributes["supported_features"] == expected_features
    else:
        assert state is None


@pytest.mark.parametrize(
    ("menuai_config", "service", "payload"),
    [
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_ARM_HOME, "ARM_HOME"),
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_ARM_AWAY, "ARM_AWAY"),
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_ARM_NIGHT, "ARM_NIGHT"),
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_ARM_VACATION, "ARM_VACATION"),
        (
            DEFAULT_CONFIG_CODE_NOT_REQUIRED,
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            "ARM_CUSTOM_BYPASS",
        ),
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_DISARM, "DISARM"),
        (DEFAULT_CONFIG_CODE_NOT_REQUIRED, SERVICE_ALARM_TRIGGER, "TRIGGER"),
    ],
)
async def test_publish_mqtt_no_code(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    service: str,
    payload: str,
) -> None:
    """Test publishing of MQTT messages when no code is configured."""
    mqtt_mock = await mqtt_mock_entry()

    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)


@pytest.mark.parametrize(
    ("menuai_config", "service", "payload", "raises"),
    [
        (
            DEFAULT_CONFIG_CODE,
            SERVICE_ALARM_ARM_HOME,
            "ARM_HOME",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_CODE,
            SERVICE_ALARM_ARM_AWAY,
            "ARM_AWAY",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_CODE,
            SERVICE_ALARM_ARM_NIGHT,
            "ARM_NIGHT",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_CODE,
            SERVICE_ALARM_ARM_VACATION,
            "ARM_VACATION",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_CODE,
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            "ARM_CUSTOM_BYPASS",
            pytest.raises(ServiceValidationError),
        ),
        (DEFAULT_CONFIG_CODE, SERVICE_ALARM_DISARM, "DISARM", does_not_raise()),
        (DEFAULT_CONFIG_CODE, SERVICE_ALARM_TRIGGER, "TRIGGER", does_not_raise()),
    ],
)
async def test_publish_mqtt_with_code(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    service: str,
    payload: str,
    raises: AbstractContextManager,
) -> None:
    """Test publishing of MQTT messages when code is configured."""
    mqtt_mock = await mqtt_mock_entry()
    call_count = mqtt_mock.async_publish.call_count

    # No code provided, should not publish
    with raises:
        await menuai.services.async_call(
            alarm_control_panel.DOMAIN,
            service,
            {ATTR_ENTITY_ID: "alarm_control_panel.test"},
            blocking=True,
        )
    assert mqtt_mock.async_publish.call_count == call_count

    # Wrong code provided, should not publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "abcd"},
        blocking=True,
    )
    assert mqtt_mock.async_publish.call_count == call_count

    # Correct code provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "0123"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)


@pytest.mark.parametrize(
    ("menuai_config", "service", "payload", "raises"),
    [
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_ARM_HOME,
            "ARM_HOME",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_ARM_AWAY,
            "ARM_AWAY",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_ARM_NIGHT,
            "ARM_NIGHT",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_ARM_VACATION,
            "ARM_VACATION",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            "ARM_CUSTOM_BYPASS",
            pytest.raises(ServiceValidationError),
        ),
        (DEFAULT_CONFIG_REMOTE_CODE, SERVICE_ALARM_DISARM, "DISARM", does_not_raise()),
        (
            DEFAULT_CONFIG_REMOTE_CODE,
            SERVICE_ALARM_TRIGGER,
            "TRIGGER",
            does_not_raise(),
        ),
    ],
)
async def test_publish_mqtt_with_remote_code(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    service: str,
    payload: str,
    raises: AbstractContextManager,
) -> None:
    """Test publishing of MQTT messages when remode code is configured."""
    mqtt_mock = await mqtt_mock_entry()
    call_count = mqtt_mock.async_publish.call_count

    # No code provided, should not publish
    with raises:
        await menuai.services.async_call(
            alarm_control_panel.DOMAIN,
            service,
            {ATTR_ENTITY_ID: "alarm_control_panel.test"},
            blocking=True,
        )
    assert mqtt_mock.async_publish.call_count == call_count

    # Any code numbered  provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "1234"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)


@pytest.mark.parametrize(
    ("menuai_config", "service", "payload", "raises"),
    [
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_ARM_HOME,
            "ARM_HOME",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_ARM_AWAY,
            "ARM_AWAY",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_ARM_NIGHT,
            "ARM_NIGHT",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_ARM_VACATION,
            "ARM_VACATION",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            "ARM_CUSTOM_BYPASS",
            pytest.raises(ServiceValidationError),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_DISARM,
            "DISARM",
            does_not_raise(),
        ),
        (
            DEFAULT_CONFIG_REMOTE_CODE_TEXT,
            SERVICE_ALARM_TRIGGER,
            "TRIGGER",
            does_not_raise(),
        ),
    ],
)
async def test_publish_mqtt_with_remote_code_text(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    service: str,
    payload: str,
    raises: AbstractContextManager,
) -> None:
    """Test publishing of MQTT messages when remote text code is configured."""
    mqtt_mock = await mqtt_mock_entry()
    call_count = mqtt_mock.async_publish.call_count

    # No code provided, should not publish
    with raises:
        await menuai.services.async_call(
            alarm_control_panel.DOMAIN,
            service,
            {ATTR_ENTITY_ID: "alarm_control_panel.test"},
            blocking=True,
        )
    assert mqtt_mock.async_publish.call_count == call_count

    # Any code numbered  provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "any_code"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)


@pytest.mark.parametrize(
    ("menuai_config", "service", "payload"),
    [
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_arm_required": False},),
            ),
            SERVICE_ALARM_ARM_HOME,
            "ARM_HOME",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_arm_required": False},),
            ),
            SERVICE_ALARM_ARM_AWAY,
            "ARM_AWAY",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_arm_required": False},),
            ),
            SERVICE_ALARM_ARM_NIGHT,
            "ARM_NIGHT",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_arm_required": False},),
            ),
            SERVICE_ALARM_ARM_VACATION,
            "ARM_VACATION",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_arm_required": False},),
            ),
            SERVICE_ALARM_ARM_CUSTOM_BYPASS,
            "ARM_CUSTOM_BYPASS",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_disarm_required": False},),
            ),
            SERVICE_ALARM_DISARM,
            "DISARM",
        ),
        (
            help_custom_config(
                alarm_control_panel.DOMAIN,
                DEFAULT_CONFIG_CODE,
                ({"code_trigger_required": False},),
            ),
            SERVICE_ALARM_TRIGGER,
            "TRIGGER",
        ),
    ],
)
async def test_publish_mqtt_with_code_required_false(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    service: str,
    payload: str,
) -> None:
    """Test publishing of MQTT messages when code is configured.

    code_arm_required = False / code_disarm_required = False /
    code_trigger_required = False
    """
    mqtt_mock = await mqtt_mock_entry()

    # No code provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)
    mqtt_mock.reset_mock()

    # Wrong code provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "abcd"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)
    mqtt_mock.reset_mock()

    # Correct code provided, should publish
    await menuai.services.async_call(
        alarm_control_panel.DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.test", ATTR_CODE: "0123"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with("alarm/command", payload, 0, False)
    mqtt_mock.reset_mock()


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN,
            DEFAULT_CONFIG_CODE,
            (
                {
                    "code": "0123",
                    "command_template": '{"action":"{{ action }}","code":"{{ code }}"}',
                },
            ),
        )
    ],
)
async def test_disarm_publishes_mqtt_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test publishing of MQTT messages while disarmed.

    When command_template set to output json
    """
    mqtt_mock = await mqtt_mock_entry()

    await common.async_alarm_disarm(menuai, "0123")
    mqtt_mock.async_publish.assert_called_once_with(
        "alarm/command", '{"action":"DISARM","code":"0123"}', 0, False
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                alarm_control_panel.DOMAIN: {
                    "name": "test",
                    "command_topic": "test-topic",
                    "state_topic": "test-topic",
                    "value_template": "\
                {% if (value | int)  == 100 %}\
                  armed_away\
                {% else %}\
                   disarmed\
                {% endif %}",
                }
            }
        }
    ],
)
async def test_update_state_via_state_topic_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test updating with template_value via state topic."""
    await mqtt_mock_entry()

    state = menuai.states.get("alarm_control_panel.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "100")

    state = menuai.states.get("alarm_control_panel.test")
    assert state.state == AlarmControlPanelState.ARMED_AWAY


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN, DEFAULT_CONFIG, ({"code": CODE_NUMBER},)
        )
    ],
)
async def test_attributes_code_number(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test attributes which are not supported by the vacuum."""
    await mqtt_mock_entry()

    state = menuai.states.get("alarm_control_panel.test")
    assert (
        state.attributes.get(alarm_control_panel.ATTR_CODE_FORMAT)
        == alarm_control_panel.CodeFormat.NUMBER
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN,
            DEFAULT_CONFIG_REMOTE_CODE,
            ({"code": "REMOTE_CODE"},),
        )
    ],
)
async def test_attributes_remote_code_number(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test attributes which are not supported by the vacuum."""
    await mqtt_mock_entry()

    state = menuai.states.get("alarm_control_panel.test")
    assert (
        state.attributes.get(alarm_control_panel.ATTR_CODE_FORMAT)
        == alarm_control_panel.CodeFormat.NUMBER
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN, DEFAULT_CONFIG, ({"code": CODE_TEXT},)
        )
    ],
)
async def test_attributes_code_text(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test attributes which are not supported by the vacuum."""
    await mqtt_mock_entry()

    state = menuai.states.get("alarm_control_panel.test")
    assert (
        state.attributes.get(alarm_control_panel.ATTR_CODE_FORMAT)
        == alarm_control_panel.CodeFormat.TEXT
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG_CODE])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG_CODE])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG_CODE
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG_CODE
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG,
        MQTT_ALARM_ATTRIBUTES_BLOCKED,
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                alarm_control_panel.DOMAIN: [
                    {
                        "name": "Test 1",
                        "state_topic": "test-topic",
                        "command_topic": "command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
                        "state_topic": "test-topic",
                        "command_topic": "command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                ]
            }
        }
    ],
)
async def test_unique_id(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unique id option only creates one alarm per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN)


async def test_discovery_removal_alarm(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered alarm_control_panel."""
    data = json.dumps(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    await help_test_discovery_removal(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, data
    )


async def test_discovery_update_alarm_topic_and_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered alarm_control_panel."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    config2 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    config1["name"] = "Beer"
    config2["name"] = "Milk"
    config1["state_topic"] = "alarm/state1"
    config2["state_topic"] = "alarm/state2"
    config1["value_template"] = "{{ value_json.state1.state }}"
    config2["value_template"] = "{{ value_json.state2.state }}"

    state_data1 = [
        ([("alarm/state1", '{"state1":{"state":"armed_away"}}')], "armed_away", None),
    ]
    state_data2 = [
        ([("alarm/state1", '{"state1":{"state":"triggered"}}')], "armed_away", None),
        ([("alarm/state1", '{"state2":{"state":"triggered"}}')], "armed_away", None),
        ([("alarm/state2", '{"state1":{"state":"triggered"}}')], "armed_away", None),
        ([("alarm/state2", '{"state2":{"state":"triggered"}}')], "triggered", None),
    ]

    await help_test_discovery_update(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        config1,
        config2,
        state_data1=state_data1,
        state_data2=state_data2,
    )


async def test_discovery_update_alarm_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered alarm_control_panel."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    config2 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    config1["name"] = "Beer"
    config2["name"] = "Milk"
    config1["state_topic"] = "alarm/state1"
    config2["state_topic"] = "alarm/state1"
    config1["value_template"] = "{{ value_json.state1.state }}"
    config2["value_template"] = "{{ value_json.state2.state }}"

    state_data1 = [
        ([("alarm/state1", '{"state1":{"state":"armed_away"}}')], "armed_away", None),
    ]
    state_data2 = [
        ([("alarm/state1", '{"state1":{"state":"triggered"}}')], "armed_away", None),
        ([("alarm/state1", '{"state2":{"state":"triggered"}}')], "triggered", None),
    ]

    await help_test_discovery_update(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        config1,
        config2,
        state_data1=state_data1,
        state_data2=state_data2,
    )


async def test_discovery_update_unchanged_alarm(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered alarm_control_panel."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN])
    config1["name"] = "Beer"

    data1 = json.dumps(config1)
    with patch(
        "menuai.components.mqtt.alarm_control_panel.MqttAlarm.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai,
            mqtt_mock_entry,
            alarm_control_panel.DOMAIN,
            data1,
            discovery_update,
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = (
        '{ "name": "Milk",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "test_topic" }'
    )
    await help_test_discovery_broken(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, data1, data2
    )


@pytest.mark.parametrize(
    ("topic", "value"),
    [
        ("state_topic", "armed_home"),
        ("state_topic", "disarmed"),
    ],
)
async def test_encoding_subscribable_topics(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    topic: str,
    value: str,
) -> None:
    """Test handling of incoming encoded payload."""
    await help_test_encoding_subscribable_topics(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG[mqtt.DOMAIN][alarm_control_panel.DOMAIN],
        topic,
        value,
    )


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT alarm control panel device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG,
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT alarm control panel device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG,
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG,
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, alarm_control_panel.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai,
        mqtt_mock_entry,
        alarm_control_panel.DOMAIN,
        DEFAULT_CONFIG,
        alarm_control_panel.SERVICE_ALARM_DISARM,
        command_payload="DISARM",
    )


@pytest.mark.parametrize(
    ("service", "topic", "parameters", "payload", "template", "tpl_par", "tpl_output"),
    [
        (
            alarm_control_panel.SERVICE_ALARM_ARM_AWAY,
            "command_topic",
            {"code": "secret"},
            "ARM_AWAY",
            "command_template",
            "code",
            b"s",
        ),
        (
            alarm_control_panel.SERVICE_ALARM_DISARM,
            "command_topic",
            {"code": "secret"},
            "DISARM",
            "command_template",
            "code",
            b"s",
        ),
    ],
)
async def test_publishing_with_custom_encoding(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    service: str,
    topic: str,
    parameters: dict[str, Any],
    payload: str,
    template: str | None,
    tpl_par: str,
    tpl_output: PublishPayloadType,
) -> None:
    """Test publishing MQTT payload with different encoding."""
    domain = alarm_control_panel.DOMAIN
    config = DEFAULT_CONFIG

    await help_test_publishing_with_custom_encoding(
        menuai,
        mqtt_mock_entry,
        caplog,
        domain,
        config,
        service,
        topic,
        parameters,
        payload,
        template,
        tpl_par=tpl_par,
        tpl_output=tpl_output,
    )


async def test_reloadable(
    menuai: menuai, mqtt_client_mock: MqttMockPahoClient
) -> None:
    """Test reloading the MQTT platform."""
    domain = alarm_control_panel.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.parametrize(
    "menuai_config",
    [DEFAULT_CONFIG, {"mqtt": [DEFAULT_CONFIG["mqtt"]]}],
    ids=["platform_key", "listed"],
)
async def test_setup_manual_entity_from_yaml(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test setup manual configured MQTT entity."""
    await mqtt_mock_entry()
    platform = alarm_control_panel.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = alarm_control_panel.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    ("expected_friendly_name", "device_class"),
    [("test", None)],
)
async def test_entity_name(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    expected_friendly_name: str | None,
    device_class: str | None,
) -> None:
    """Test the entity name setup."""
    domain = alarm_control_panel.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_name(
        menuai, mqtt_mock_entry, domain, config, expected_friendly_name, device_class
    )


async def test_entity_icon_and_entity_picture(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test the entity icon or picture setup."""
    domain = alarm_control_panel.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_icon_and_entity_picture(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "availability_topic": "availability-topic",
                    "json_attributes_topic": "json-attributes-topic",
                    "state_topic": "test-topic",
                },
            ),
        )
    ],
)
@pytest.mark.parametrize(
    ("topic", "payload1", "payload2"),
    [
        (
            "test-topic",
            AlarmControlPanelState.DISARMED,
            AlarmControlPanelState.ARMED_HOME,
        ),
        ("availability-topic", "online", "offline"),
        ("json-attributes-topic", '{"attr1": "val1"}', '{"attr1": "val2"}'),
    ],
)
async def test_skipped_async_ha_write_state(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    topic: str,
    payload1: str,
    payload2: str,
) -> None:
    """Test a write state command is only called when there is change."""
    await mqtt_mock_entry()
    await help_test_skipped_async_ha_write_state(menuai, topic, payload1, payload2)


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            "mqtt": [
                {
                    "alarm_control_panel": {
                        "name": "test",
                        "invalid_topic": "test-topic",
                    }
                },
            ]
        }
    ],
)
async def test_reload_after_invalid_config(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reloading yaml config fails."""
    with patch(
        "menuai.components.mqtt.ir.async_delete_issue"
    ) as mock_async_remove_issue:
        assert await mqtt_mock_entry()
        assert menuai.states.get("alarm_control_panel.test") is None
        assert (
            "extra keys not allowed @ data['invalid_topic'] for "
            "manually configured MQTT alarm_control_panel item, "
            "in ?, line ? Got {'name': 'test', 'invalid_topic': 'test-topic'}"
            in caplog.text
        )

        # Reload with an valid config
        valid_config = {
            "mqtt": [
                {
                    "alarm_control_panel": {
                        "name": "test",
                        "command_topic": "test-topic",
                        "state_topic": "alarm/state",
                    }
                },
            ]
        }
        with patch(
            "menuai.config.load_yaml_config_file", return_value=valid_config
        ):
            await menuai.services.async_call(
                "mqtt",
                SERVICE_RELOAD,
                {},
                blocking=True,
            )
            await menuai.async_block_till_done()

        # Test the config is loaded now and that the existing issue is removed
        assert menuai.states.get("alarm_control_panel.test") is not None
        assert mock_async_remove_issue.call_count == 1

        # Reload with an invalid config
        invalid_config = {
            "mqtt": [
                {
                    "alarm_control_panel": {
                        "name": "test",
                        "command_topic": "test-topic",
                        "invalid_option": "should_fail",
                    }
                },
            ]
        }
        with (
            patch(
                "menuai.config.load_yaml_config_file",
                return_value=invalid_config,
            ),
            pytest.raises(menuaiError),
        ):
            await menuai.services.async_call(
                "mqtt",
                SERVICE_RELOAD,
                {},
                blocking=True,
            )

        # Make sure the config is loaded now
        assert menuai.states.get("alarm_control_panel.test") is not None


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            alarm_control_panel.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "state_topic": "test-topic",
                    "value_template": "{{ value_json.some_var * 1 }}",
                },
            ),
        )
    ],
)
async def test_value_template_fails(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the rendering of MQTT value template fails."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(menuai, "test-topic", '{"some_var": null }')
    assert (
        "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int' rendering template"
        in caplog.text
    )
