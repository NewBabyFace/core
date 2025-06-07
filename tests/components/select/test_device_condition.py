"""The tests for Select device conditions."""

from __future__ import annotations

import pytest
from pytest_unordered import unordered
import voluptuous_serialize

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.select import DOMAIN
from menuai.components.select.device_condition import (
    async_get_condition_capabilities,
)
from menuai.const import EntityCategory
from menuai.core import menuai, ServiceCall
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


async def test_get_conditions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected conditions from a select."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    expected_conditions = [
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": "selected_option",
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (er.RegistryEntryHider.INTEGRATION, None),
        (er.RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_conditions_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by,
    entity_category,
) -> None:
    """Test we get the expected conditions from a hidden or auxiliary entity."""
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
    expected_conditions = [
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": condition,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": True},
        }
        for condition in ("selected_option",)
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


async def test_if_selected_option(
    menuai: menuai,
    service_calls: list[ServiceCall],
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for selected_option conditions."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event1"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "selected_option",
                            "option": "option1",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data": {
                            "result": "option1 - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event2"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "selected_option",
                            "option": "option2",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data": {
                            "result": "option2 - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
            ]
        },
    )

    # Test with non existing entity
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    menuai.states.async_set(
        entry.entity_id, "option1", {"options": ["option1", "option2"]}
    )
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["result"] == "option1 - event - test_event1"

    menuai.states.async_set(
        entry.entity_id, "option2", {"options": ["option1", "option2"]}
    )
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["result"] == "option2 - event - test_event2"


async def test_if_selected_option_legacy(
    menuai: menuai,
    service_calls: list[ServiceCall],
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for selected_option conditions."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event1"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.entity_id,
                            "type": "selected_option",
                            "option": "option1",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data": {
                            "result": "option1 - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
            ]
        },
    )

    menuai.states.async_set(
        entry.entity_id, "option1", {"options": ["option1", "option2"]}
    )
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["result"] == "option1 - event - test_event1"


async def test_get_condition_capabilities(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test we get the expected capabilities from a select condition."""
    entry = entity_registry.async_get_or_create(DOMAIN, "test", "5678")

    config = {
        "platform": "device",
        "domain": DOMAIN,
        "type": "selected_option",
        "entity_id": entry.id,
        "option": "option1",
    }

    # Test when entity doesn't exists
    capabilities = await async_get_condition_capabilities(menuai, config)
    assert capabilities
    assert "extra_fields" in capabilities
    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "option",
            "required": True,
            "type": "select",
            "options": [],
        },
        {
            "name": "for",
            "optional": True,
            "type": "positive_time_period_dict",
        },
    ]

    # Mock an entity
    menuai.states.async_set(
        entry.entity_id, "option1", {"options": ["option1", "option2"]}
    )

    # Test if we get the right capabilities now
    capabilities = await async_get_condition_capabilities(menuai, config)
    assert capabilities
    assert "extra_fields" in capabilities
    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "option",
            "required": True,
            "type": "select",
            "options": [("option1", "option1"), ("option2", "option2")],
        },
        {
            "name": "for",
            "optional": True,
            "type": "positive_time_period_dict",
        },
    ]


async def test_get_condition_capabilities_legacy(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test we get the expected capabilities from a select condition."""
    entry = entity_registry.async_get_or_create(DOMAIN, "test", "5678")

    config = {
        "platform": "device",
        "domain": DOMAIN,
        "type": "selected_option",
        "entity_id": entry.entity_id,
        "option": "option1",
    }

    # Test when entity doesn't exists
    capabilities = await async_get_condition_capabilities(menuai, config)
    assert capabilities
    assert "extra_fields" in capabilities
    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "option",
            "required": True,
            "type": "select",
            "options": [],
        },
        {
            "name": "for",
            "optional": True,
            "type": "positive_time_period_dict",
        },
    ]

    # Mock an entity
    menuai.states.async_set(
        entry.entity_id, "option1", {"options": ["option1", "option2"]}
    )

    # Test if we get the right capabilities now
    capabilities = await async_get_condition_capabilities(menuai, config)
    assert capabilities
    assert "extra_fields" in capabilities
    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "option",
            "required": True,
            "type": "select",
            "options": [("option1", "option1"), ("option2", "option2")],
        },
        {
            "name": "for",
            "optional": True,
            "type": "positive_time_period_dict",
        },
    ]
