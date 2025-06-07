"""The tests for Alarm control panel device triggers."""

from datetime import timedelta

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.alarm_control_panel import (
    DOMAIN,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from menuai.components.device_automation import DeviceAutomationType
from menuai.const import EntityCategory
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_get_device_automation_capabilities,
    async_get_device_automations,
)


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.mark.parametrize(
    ("set_state", "features_reg", "features_state", "expected_trigger_types"),
    [
        (False, 0, 0, ["triggered", "disarmed", "arming"]),
        (
            False,
            47,
            0,
            [
                "triggered",
                "disarmed",
                "arming",
                "armed_home",
                "armed_away",
                "armed_night",
                "armed_vacation",
            ],
        ),
        (True, 0, 0, ["triggered", "disarmed", "arming"]),
        (
            True,
            0,
            47,
            [
                "triggered",
                "disarmed",
                "arming",
                "armed_home",
                "armed_away",
                "armed_night",
                "armed_vacation",
            ],
        ),
    ],
)
async def test_get_triggers(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state: bool,
    features_reg: AlarmControlPanelEntityFeature,
    features_state: AlarmControlPanelEntityFeature,
    expected_trigger_types: list[str],
) -> None:
    """Test we get the expected triggers from an alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        supported_features=features_reg,
    )
    if set_state:
        menuai.states.async_set(
            entry.entity_id,
            "attributes",
            {"supported_features": features_state},
        )
    expected_triggers = []

    expected_triggers += [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entry.id,
            "metadata": {"secondary": False},
        }
        for trigger in expected_trigger_types
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (er.RegistryEntryHider.INTEGRATION, None),
        (er.RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_triggers_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by: er.RegistryEntryHider | None,
    entity_category: EntityCategory | None,
) -> None:
    """Test we get the expected triggers from a hidden or auxiliary entity."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        entity_category=entity_category,
        hidden_by=hidden_by,
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entry.id,
            "metadata": {"secondary": True},
        }
        for trigger in ("triggered", "disarmed", "arming")
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


async def test_get_trigger_capabilities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from an alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    menuai.states.async_set(
        "alarm_control_panel.test_5678", "attributes", {"supported_features": 15}
    )

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 6
    for trigger in triggers:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.TRIGGER, trigger
        )
        assert capabilities == {
            "extra_fields": [
                {"name": "for", "optional": True, "type": "positive_time_period_dict"}
            ]
        }


async def test_get_trigger_capabilities_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from an alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    menuai.states.async_set(
        "alarm_control_panel.test_5678", "attributes", {"supported_features": 15}
    )

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 6
    for trigger in triggers:
        trigger["entity_id"] = entity_registry.async_get(trigger["entity_id"]).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.TRIGGER, trigger
        )
        assert capabilities == {
            "extra_fields": [
                {"name": "for", "optional": True, "type": "positive_time_period_dict"}
            ]
        }


async def test_if_fires_on_state_change(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for turn_on and turn_off triggers firing."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.PENDING)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "triggered",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "triggered "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "disarmed",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "disarmed "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "armed_home",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_home "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "armed_away",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_away "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "armed_night",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_night "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "armed_vacation",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_vacation "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ trigger.from_state.state }} "
                                "- {{ trigger.to_state.state }} "
                                "- {{ trigger.for }}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is triggered.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.TRIGGERED)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"triggered - device - {entry.entity_id} - pending - triggered - None"
    )

    # Fake that the entity is disarmed.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.DISARMED)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert (
        service_calls[1].data["some"]
        == f"disarmed - device - {entry.entity_id} - triggered - disarmed - None"
    )

    # Fake that the entity is armed home.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.ARMED_HOME)
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert (
        service_calls[2].data["some"]
        == f"armed_home - device - {entry.entity_id} - disarmed - armed_home - None"
    )

    # Fake that the entity is armed away.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.ARMED_AWAY)
    await menuai.async_block_till_done()
    assert len(service_calls) == 4
    assert (
        service_calls[3].data["some"]
        == f"armed_away - device - {entry.entity_id} - armed_home - armed_away - None"
    )

    # Fake that the entity is armed night.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.ARMED_NIGHT)
    await menuai.async_block_till_done()
    assert len(service_calls) == 5
    assert (
        service_calls[4].data["some"]
        == f"armed_night - device - {entry.entity_id} - armed_away - armed_night - None"
    )

    # Fake that the entity is armed vacation.
    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.ARMED_VACATION)
    await menuai.async_block_till_done()
    assert len(service_calls) == 6
    assert (
        service_calls[5].data["some"]
        == f"armed_vacation - device - {entry.entity_id} - armed_night - armed_vacation - None"
    )


async def test_if_fires_on_state_change_with_for(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for triggers firing with delay."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.DISARMED)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "triggered",
                        "for": {"seconds": 5},
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "turn_off {{ trigger.platform }}"
                                " - {{ trigger.entity_id }}"
                                " - {{ trigger.from_state.state }}"
                                " - {{ trigger.to_state.state }}"
                                " - {{ trigger.for }}"
                            )
                        },
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.TRIGGERED)
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    await menuai.async_block_till_done()
    assert (
        service_calls[0].data["some"]
        == f"turn_off device - {entry.entity_id} - disarmed - triggered - 0:00:05"
    )


async def test_if_fires_on_state_change_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for triggers firing with delay."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.DISARMED)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.entity_id,
                        "type": "triggered",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "turn_off {{ trigger.platform }}"
                                " - {{ trigger.entity_id }}"
                                " - {{ trigger.from_state.state }}"
                                " - {{ trigger.to_state.state }}"
                                " - {{ trigger.for }}"
                            )
                        },
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    menuai.states.async_set(entry.entity_id, AlarmControlPanelState.TRIGGERED)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"turn_off device - {entry.entity_id} - disarmed - triggered - None"
    )
