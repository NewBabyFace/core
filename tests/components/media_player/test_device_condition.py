"""The tests for Media player device conditions."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.media_player import DOMAIN
from menuai.const import (
    STATE_BUFFERING,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    EntityCategory,
)
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


async def test_get_conditions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected conditions from a media_player."""
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
            "type": condition,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for condition in (
            "is_buffering",
            "is_off",
            "is_on",
            "is_idle",
            "is_paused",
            "is_playing",
        )
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (RegistryEntryHider.INTEGRATION, None),
        (RegistryEntryHider.USER, None),
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
        for condition in (
            "is_buffering",
            "is_off",
            "is_on",
            "is_idle",
            "is_paused",
            "is_playing",
        )
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


async def test_if_state(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for turn_on and turn_off conditions."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(entry.entity_id, STATE_ON)

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
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
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
                {
                    "trigger": {"platform": "event", "event_type": "test_event3"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "is_idle",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_idle - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event4"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "is_paused",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_paused - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event5"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "is_playing",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_playing - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event6"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": device_entry.id,
                            "entity_id": entry.id,
                            "type": "is_buffering",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_buffering - {{ trigger.platform }} - {{ trigger.event.event_type }}"
                        },
                    },
                },
            ]
        },
    )
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "is_on - event - test_event1"

    menuai.states.async_set(entry.entity_id, STATE_OFF)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "is_off - event - test_event2"

    menuai.states.async_set(entry.entity_id, STATE_IDLE)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert service_calls[2].data["some"] == "is_idle - event - test_event3"

    menuai.states.async_set(entry.entity_id, STATE_PAUSED)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 4
    assert service_calls[3].data["some"] == "is_paused - event - test_event4"

    menuai.states.async_set(entry.entity_id, STATE_PLAYING)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 5
    assert service_calls[4].data["some"] == "is_playing - event - test_event5"

    menuai.states.async_set(entry.entity_id, STATE_BUFFERING)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    menuai.bus.async_fire("test_event4")
    menuai.bus.async_fire("test_event5")
    menuai.bus.async_fire("test_event6")
    await menuai.async_block_till_done()
    assert len(service_calls) == 6
    assert service_calls[5].data["some"] == "is_buffering - event - test_event6"


async def test_if_state_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for turn_on and turn_off conditions."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(entry.entity_id, STATE_ON)

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
            ]
        },
    )
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "is_on - event - test_event1"
