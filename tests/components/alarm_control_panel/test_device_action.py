"""The tests for Alarm control panel device actions."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.alarm_control_panel import (
    DOMAIN,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from menuai.components.device_automation import DeviceAutomationType
from menuai.const import CONF_PLATFORM, STATE_UNKNOWN, EntityCategory
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .common import MockAlarm

from tests.common import (
    MockConfigEntry,
    async_get_device_automation_capabilities,
    async_get_device_automations,
    setup_test_component_platform,
)


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.mark.parametrize(
    ("set_state", "features_reg", "features_state", "expected_action_types"),
    [
        (False, 0, 0, ["disarm"]),
        (
            False,
            AlarmControlPanelEntityFeature.ARM_AWAY,
            0,
            ["disarm", "arm_away"],
        ),
        (
            False,
            AlarmControlPanelEntityFeature.ARM_HOME,
            0,
            ["disarm", "arm_home"],
        ),
        (
            False,
            AlarmControlPanelEntityFeature.ARM_NIGHT,
            0,
            ["disarm", "arm_night"],
        ),
        (False, AlarmControlPanelEntityFeature.TRIGGER, 0, ["disarm", "trigger"]),
        (True, 0, 0, ["disarm"]),
        (
            True,
            0,
            AlarmControlPanelEntityFeature.ARM_AWAY,
            ["disarm", "arm_away"],
        ),
        (
            True,
            0,
            AlarmControlPanelEntityFeature.ARM_HOME,
            ["disarm", "arm_home"],
        ),
        (
            True,
            0,
            AlarmControlPanelEntityFeature.ARM_NIGHT,
            ["disarm", "arm_night"],
        ),
        (
            True,
            0,
            AlarmControlPanelEntityFeature.ARM_VACATION,
            ["disarm", "arm_vacation"],
        ),
        (True, 0, AlarmControlPanelEntityFeature.TRIGGER, ["disarm", "trigger"]),
    ],
)
async def test_get_actions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state: bool,
    features_reg: AlarmControlPanelEntityFeature,
    features_state: AlarmControlPanelEntityFeature,
    expected_action_types: list[str],
) -> None:
    """Test we get the expected actions from a alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        supported_features=features_reg,
    )
    if set_state:
        menuai.states.async_set(
            f"{DOMAIN}.test_5678", "attributes", {"supported_features": features_state}
        )
    expected_actions = [
        {
            "domain": DOMAIN,
            "type": action,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for action in expected_action_types
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (er.RegistryEntryHider.INTEGRATION, None),
        (er.RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_actions_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by: er.RegistryEntryHider | None,
    entity_category: EntityCategory | None,
) -> None:
    """Test we get the expected actions from a hidden or auxiliary entity."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        entity_category=entity_category,
        hidden_by=hidden_by,
        supported_features=AlarmControlPanelEntityFeature.ARM_AWAY,
    )
    expected_actions = []
    expected_actions += [
        {
            "domain": DOMAIN,
            "type": action,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": True},
        }
        for action in ("disarm", "arm_away")
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


async def test_get_actions_arm_night_only(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected actions from a alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    menuai.states.async_set(
        "alarm_control_panel.test_5678", "attributes", {"supported_features": 4}
    )
    expected_actions = [
        {
            "domain": DOMAIN,
            "type": "arm_night",
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        },
        {
            "domain": DOMAIN,
            "type": "disarm",
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        },
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


async def test_get_action_capabilities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test we get the expected capabilities from a sensor trigger."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["no_arm_code"].unique_id,
        device_id=device_entry.id,
    )

    expected_capabilities = {
        "arm_away": {"extra_fields": []},
        "arm_home": {"extra_fields": []},
        "arm_night": {"extra_fields": []},
        "arm_vacation": {"extra_fields": []},
        "disarm": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "trigger": {"extra_fields": []},
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 6
    assert {action["type"] for action in actions} == set(expected_capabilities)
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == expected_capabilities[action["type"]]


async def test_get_action_capabilities_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test we get the expected capabilities from a sensor trigger."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["no_arm_code"].unique_id,
        device_id=device_entry.id,
    )

    expected_capabilities = {
        "arm_away": {"extra_fields": []},
        "arm_home": {"extra_fields": []},
        "arm_night": {"extra_fields": []},
        "arm_vacation": {"extra_fields": []},
        "disarm": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "trigger": {"extra_fields": []},
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 6
    assert {action["type"] for action in actions} == set(expected_capabilities)
    for action in actions:
        action["entity_id"] = entity_registry.async_get(action["entity_id"]).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == expected_capabilities[action["type"]]


async def test_get_action_capabilities_arm_code(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test we get the expected capabilities from a sensor trigger."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["arm_code"].unique_id,
        device_id=device_entry.id,
    )

    expected_capabilities = {
        "arm_away": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_home": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_night": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_vacation": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "disarm": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "trigger": {"extra_fields": []},
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 6
    assert {action["type"] for action in actions} == set(expected_capabilities)
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == expected_capabilities[action["type"]]


async def test_get_action_capabilities_arm_code_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test we get the expected capabilities from a sensor trigger."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["arm_code"].unique_id,
        device_id=device_entry.id,
    )

    expected_capabilities = {
        "arm_away": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_home": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_night": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "arm_vacation": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "disarm": {
            "extra_fields": [{"name": "code", "optional": True, "type": "string"}]
        },
        "trigger": {"extra_fields": []},
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 6
    assert {action["type"] for action in actions} == set(expected_capabilities)
    for action in actions:
        action["entity_id"] = entity_registry.async_get(action["entity_id"]).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == expected_capabilities[action["type"]]


async def test_action(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test for turn_on and turn_off actions."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["no_arm_code"].unique_id,
        device_id=device_entry.id,
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_arm_away",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "arm_away",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_arm_home",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "arm_home",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_arm_night",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "arm_night",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_arm_vacation",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "arm_vacation",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_disarm"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "disarm",
                        "code": "1234",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_trigger",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.id,
                        "type": "trigger",
                    },
                },
            ]
        },
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_entry.entity_id).state == STATE_UNKNOWN

    menuai.bus.async_fire("test_event_arm_away")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.ARMED_AWAY
    )

    menuai.bus.async_fire("test_event_arm_home")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.ARMED_HOME
    )

    menuai.bus.async_fire("test_event_arm_vacation")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.ARMED_VACATION
    )

    menuai.bus.async_fire("test_event_arm_night")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.ARMED_NIGHT
    )

    menuai.bus.async_fire("test_event_disarm")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state == AlarmControlPanelState.DISARMED
    )

    menuai.bus.async_fire("test_event_trigger")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.TRIGGERED
    )


async def test_action_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_alarm_control_panel_entities: dict[str, MockAlarm],
) -> None:
    """Test for turn_on and turn_off actions."""
    setup_test_component_platform(
        menuai, DOMAIN, mock_alarm_control_panel_entities.values()
    )

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        mock_alarm_control_panel_entities["no_arm_code"].unique_id,
        device_id=device_entry.id,
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_arm_away",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entity_entry.entity_id,
                        "type": "arm_away",
                    },
                },
            ]
        },
    )
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_entry.entity_id).state == STATE_UNKNOWN

    menuai.bus.async_fire("test_event_arm_away")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get(entity_entry.entity_id).state
        == AlarmControlPanelState.ARMED_AWAY
    )
