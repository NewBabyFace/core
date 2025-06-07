"""The tests for Vacuum device triggers."""

from datetime import timedelta

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.vacuum import DOMAIN, VacuumActivity
from menuai.const import EntityCategory
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
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


async def test_get_triggers(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected triggers from a vacuum."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for trigger in ("cleaning", "docked")
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (RegistryEntryHider.INTEGRATION, None),
        (RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_triggers_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by,
    entity_category,
) -> None:
    """Test we get the expected triggers from a hidden or auxiliary entity."""
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
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": True},
        }
        for trigger in ("cleaning", "docked")
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
    """Test we get the expected capabilities from a vacuum device."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 2
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
    """Test we get the expected capabilities from a vacuum device."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 2
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

    menuai.states.async_set(entry.entity_id, VacuumActivity.DOCKED)

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
                        "type": "cleaning",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "cleaning - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}}"
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
                        "type": "docked",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "docked - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is cleaning
    menuai.states.async_set(entry.entity_id, VacuumActivity.CLEANING)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"cleaning - device - {entry.entity_id} - docked - cleaning"
    )

    # Fake that the entity is docked
    menuai.states.async_set(entry.entity_id, VacuumActivity.DOCKED)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert (
        service_calls[1].data["some"]
        == f"docked - device - {entry.entity_id} - cleaning - docked"
    )


async def test_if_fires_on_state_change_legacy(
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

    menuai.states.async_set(entry.entity_id, VacuumActivity.DOCKED)

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
                        "type": "cleaning",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "cleaning - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is cleaning
    menuai.states.async_set(entry.entity_id, VacuumActivity.CLEANING)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"cleaning - device - {entry.entity_id} - docked - cleaning"
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

    menuai.states.async_set(entry.entity_id, VacuumActivity.DOCKED)

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
                        "type": "cleaning",
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

    menuai.states.async_set(entry.entity_id, VacuumActivity.CLEANING)
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    await menuai.async_block_till_done()
    assert (
        service_calls[0].data["some"]
        == f"turn_off device - {entry.entity_id} - docked - cleaning - 0:00:05"
    )
