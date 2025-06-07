"""The tests for Cover device conditions."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.cover import DOMAIN, CoverEntityFeature, CoverState
from menuai.components.device_automation import DeviceAutomationType
from menuai.const import CONF_PLATFORM, STATE_UNAVAILABLE, EntityCategory
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from .common import MockCover

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
    ("set_state", "features_reg", "features_state", "expected_condition_types"),
    [
        (False, 0, 0, []),
        (
            False,
            CoverEntityFeature.CLOSE,
            0,
            ["is_open", "is_closed", "is_opening", "is_closing"],
        ),
        (
            False,
            CoverEntityFeature.OPEN,
            0,
            ["is_open", "is_closed", "is_opening", "is_closing"],
        ),
        (False, CoverEntityFeature.SET_POSITION, 0, ["is_position"]),
        (False, CoverEntityFeature.SET_TILT_POSITION, 0, ["is_tilt_position"]),
        (True, 0, 0, []),
        (
            True,
            0,
            CoverEntityFeature.CLOSE,
            ["is_open", "is_closed", "is_opening", "is_closing"],
        ),
        (
            True,
            0,
            CoverEntityFeature.OPEN,
            ["is_open", "is_closed", "is_opening", "is_closing"],
        ),
        (True, 0, CoverEntityFeature.SET_POSITION, ["is_position"]),
        (True, 0, CoverEntityFeature.SET_TILT_POSITION, ["is_tilt_position"]),
    ],
)
async def test_get_conditions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state,
    features_reg,
    features_state,
    expected_condition_types,
) -> None:
    """Test we get the expected conditions from a cover."""
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
    await menuai.async_block_till_done()

    expected_conditions = []
    expected_conditions += [
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": condition,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for condition in expected_condition_types
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
        supported_features=CoverEntityFeature.CLOSE,
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
        for condition in ("is_open", "is_closed", "is_opening", "is_closing")
    ]
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert conditions == unordered(expected_conditions)


async def test_get_condition_capabilities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover condition."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)
    ent = mock_cover_entities[0]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", ent.unique_id, device_id=device_entry.id
    )

    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert len(conditions) == 4
    for condition in conditions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.CONDITION, condition
        )
        assert capabilities == {"extra_fields": []}


async def test_get_condition_capabilities_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover condition."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)
    ent = mock_cover_entities[0]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", ent.unique_id, device_id=device_entry.id
    )

    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert len(conditions) == 4
    for condition in conditions:
        condition["entity_id"] = entity_registry.async_get(
            condition["entity_id"]
        ).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.CONDITION, condition
        )
        assert capabilities == {"extra_fields": []}


async def test_get_condition_capabilities_set_pos(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover condition."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)
    ent = mock_cover_entities[1]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", ent.unique_id, device_id=device_entry.id
    )

    expected_capabilities = {
        "extra_fields": [
            {
                "name": "above",
                "optional": True,
                "type": "integer",
                "default": 0,
                "valueMax": 100,
                "valueMin": 0,
            },
            {
                "name": "below",
                "optional": True,
                "type": "integer",
                "default": 100,
                "valueMax": 100,
                "valueMin": 0,
            },
        ]
    }
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert len(conditions) == 5
    for condition in conditions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.CONDITION, condition
        )
        if condition["type"] == "is_position":
            assert capabilities == expected_capabilities
        else:
            assert capabilities == {"extra_fields": []}


async def test_get_condition_capabilities_set_tilt_pos(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover condition."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)

    ent = mock_cover_entities[3]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", ent.unique_id, device_id=device_entry.id
    )

    expected_capabilities = {
        "extra_fields": [
            {
                "name": "above",
                "optional": True,
                "type": "integer",
                "default": 0,
                "valueMax": 100,
                "valueMin": 0,
            },
            {
                "name": "below",
                "optional": True,
                "type": "integer",
                "default": 100,
                "valueMax": 100,
                "valueMin": 0,
            },
        ]
    }
    conditions = await async_get_device_automations(
        menuai, DeviceAutomationType.CONDITION, device_entry.id
    )
    assert len(conditions) == 5
    for condition in conditions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.CONDITION, condition
        )
        if condition["type"] == "is_tilt_position":
            assert capabilities == expected_capabilities
        else:
            assert capabilities == {"extra_fields": []}


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

    menuai.states.async_set(entry.entity_id, CoverState.OPEN)

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
                            "type": "is_open",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_open "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
                            "type": "is_closed",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_closed "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
                            "type": "is_opening",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_opening "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
                            "type": "is_closing",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_closing "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
    assert service_calls[0].data["some"] == "is_open - event - test_event1"

    menuai.states.async_set(entry.entity_id, CoverState.CLOSED)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "is_closed - event - test_event2"

    menuai.states.async_set(entry.entity_id, CoverState.OPENING)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert service_calls[2].data["some"] == "is_opening - event - test_event3"

    menuai.states.async_set(entry.entity_id, CoverState.CLOSING)
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event4")
    await menuai.async_block_till_done()
    assert len(service_calls) == 4
    assert service_calls[3].data["some"] == "is_closing - event - test_event4"


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

    menuai.states.async_set(entry.entity_id, CoverState.OPEN)

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
                            "type": "is_open",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_open "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
    assert service_calls[0].data["some"] == "is_open - event - test_event1"


async def test_if_position(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for position conditions."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)
    ent = mock_cover_entities[1]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get(ent.entity_id)
    entity_registry.async_update_entity(entry.entity_id, device_id=device_entry.id)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event1"},
                    "action": {
                        "choose": {
                            "conditions": {
                                "condition": "device",
                                "domain": DOMAIN,
                                "device_id": device_entry.id,
                                "entity_id": entry.id,
                                "type": "is_position",
                                "above": 45,
                            },
                            "sequence": {
                                "service": "test.automation",
                                "data_template": {
                                    "some": (
                                        "is_pos_gt_45 "
                                        "- {{ trigger.platform }} "
                                        "- {{ trigger.event.event_type }}"
                                    )
                                },
                            },
                        },
                        "default": {
                            "service": "test.automation",
                            "data_template": {
                                "some": (
                                    "is_pos_not_gt_45 "
                                    "- {{ trigger.platform }} "
                                    "- {{ trigger.event.event_type }}"
                                )
                            },
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
                            "type": "is_position",
                            "below": 90,
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_pos_lt_90 "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
                            "type": "is_position",
                            "above": 45,
                            "below": 90,
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_pos_gt_45_lt_90 "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
                        },
                    },
                },
            ]
        },
    )

    caplog.clear()

    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert service_calls[0].data["some"] == "is_pos_gt_45 - event - test_event1"
    assert service_calls[1].data["some"] == "is_pos_lt_90 - event - test_event2"
    assert service_calls[2].data["some"] == "is_pos_gt_45_lt_90 - event - test_event3"

    menuai.states.async_set(
        ent.entity_id, CoverState.CLOSED, attributes={"current_position": 45}
    )
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 5
    assert service_calls[3].data["some"] == "is_pos_not_gt_45 - event - test_event1"
    assert service_calls[4].data["some"] == "is_pos_lt_90 - event - test_event2"

    menuai.states.async_set(
        ent.entity_id, CoverState.CLOSED, attributes={"current_position": 90}
    )
    menuai.bus.async_fire("test_event1")
    menuai.bus.async_fire("test_event2")
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 6
    assert service_calls[5].data["some"] == "is_pos_gt_45 - event - test_event1"

    menuai.states.async_set(ent.entity_id, STATE_UNAVAILABLE, attributes={})
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    assert len(service_calls) == 7
    assert service_calls[6].data["some"] == "is_pos_not_gt_45 - event - test_event1"

    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")


async def test_if_tilt_position(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for tilt position conditions."""
    setup_test_component_platform(menuai, DOMAIN, mock_cover_entities)
    ent = mock_cover_entities[3]
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get(ent.entity_id)
    entity_registry.async_update_entity(entry.entity_id, device_id=device_entry.id)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event1"},
                    "action": {
                        "choose": {
                            "conditions": {
                                "condition": "device",
                                "domain": DOMAIN,
                                "device_id": device_entry.id,
                                "entity_id": entry.id,
                                "type": "is_tilt_position",
                                "above": 45,
                            },
                            "sequence": {
                                "service": "test.automation",
                                "data_template": {
                                    "some": (
                                        "is_pos_gt_45 "
                                        "- {{ trigger.platform }} "
                                        "- {{ trigger.event.event_type }}"
                                    )
                                },
                            },
                        },
                        "default": {
                            "service": "test.automation",
                            "data_template": {
                                "some": (
                                    "is_pos_not_gt_45 "
                                    "- {{ trigger.platform }} "
                                    "- {{ trigger.event.event_type }}"
                                )
                            },
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
                            "type": "is_tilt_position",
                            "below": 90,
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_pos_lt_90 "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
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
                            "type": "is_tilt_position",
                            "above": 45,
                            "below": 90,
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "is_pos_gt_45_lt_90 "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.event.event_type }}"
                            )
                        },
                    },
                },
            ]
        },
    )

    caplog.clear()

    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert service_calls[0].data["some"] == "is_pos_gt_45 - event - test_event1"
    assert service_calls[1].data["some"] == "is_pos_lt_90 - event - test_event2"
    assert service_calls[2].data["some"] == "is_pos_gt_45_lt_90 - event - test_event3"

    menuai.states.async_set(
        ent.entity_id, CoverState.CLOSED, attributes={"current_tilt_position": 45}
    )
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 5
    assert service_calls[3].data["some"] == "is_pos_not_gt_45 - event - test_event1"
    assert service_calls[4].data["some"] == "is_pos_lt_90 - event - test_event2"

    menuai.states.async_set(
        ent.entity_id, CoverState.CLOSED, attributes={"current_tilt_position": 90}
    )
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event2")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("test_event3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 6
    assert service_calls[5].data["some"] == "is_pos_gt_45 - event - test_event1"

    menuai.states.async_set(ent.entity_id, STATE_UNAVAILABLE, attributes={})
    menuai.bus.async_fire("test_event1")
    await menuai.async_block_till_done()
    assert len(service_calls) == 7
    assert service_calls[6].data["some"] == "is_pos_not_gt_45 - event - test_event1"

    for record in caplog.records:
        assert record.levelname in ("DEBUG", "INFO")
