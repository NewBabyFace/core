"""The tests for NEW_NAME device conditions."""

from __future__ import annotations

from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.NEW_DOMAIN import DOMAIN
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


async def test_get_conditions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected conditions from a NEW_DOMAIN."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    expected_conditions = [
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": "is_off",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": "is_on",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


async def test_if_state(menuai: menuai, service_calls: list[ServiceCall]) -> None:
    """Test for turn_on and turn_off conditions."""
    menuai.states.async_set("NEW_DOMAIN.entity", STATE_ON)

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
                            "device_id": "",
                            "entity_id": "NEW_DOMAIN.entity",
                            "type": "is_on",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_on - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event2"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": "",
                            "entity_id": "NEW_DOMAIN.entity",
                            "type": "is_off",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_off - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
            ]
        },
    )
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "is_on - event - test_event1"

    menuai.states.async_set("NEW_DOMAIN.entity", STATE_OFF)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "is_off - event - test_event2"
