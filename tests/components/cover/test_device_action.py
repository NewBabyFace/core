"""The tests for Cover device actions."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.cover import DOMAIN, CoverEntityFeature
from menuai.components.device_automation import DeviceAutomationType
from menuai.const import CONF_PLATFORM, EntityCategory
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from .common import MockCover

from tests.common import (
    MockConfigEntry,
    async_get_device_automation_capabilities,
    async_get_device_automations,
    async_mock_service,
    setup_test_component_platform,
)


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.mark.parametrize(
    ("set_state", "features_reg", "features_state", "expected_action_types"),
    [
        (False, 0, 0, []),
        (False, CoverEntityFeature.CLOSE_TILT, 0, ["close_tilt"]),
        (False, CoverEntityFeature.CLOSE, 0, ["close"]),
        (False, CoverEntityFeature.OPEN_TILT, 0, ["open_tilt"]),
        (False, CoverEntityFeature.OPEN, 0, ["open"]),
        (False, CoverEntityFeature.SET_POSITION, 0, ["set_position"]),
        (False, CoverEntityFeature.SET_TILT_POSITION, 0, ["set_tilt_position"]),
        (False, CoverEntityFeature.STOP, 0, ["stop"]),
        (True, 0, 0, []),
        (True, 0, CoverEntityFeature.CLOSE_TILT, ["close_tilt"]),
        (True, 0, CoverEntityFeature.CLOSE, ["close"]),
        (True, 0, CoverEntityFeature.OPEN_TILT, ["open_tilt"]),
        (True, 0, CoverEntityFeature.OPEN, ["open"]),
        (True, 0, CoverEntityFeature.SET_POSITION, ["set_position"]),
        (True, 0, CoverEntityFeature.SET_TILT_POSITION, ["set_tilt_position"]),
        (True, 0, CoverEntityFeature.STOP, ["stop"]),
    ],
)
async def test_get_actions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state,
    features_reg,
    features_state,
    expected_action_types,
) -> None:
    """Test we get the expected actions from a cover."""
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
            entity_entry.entity_id, "attributes", {"supported_features": features_state}
        )
    await menuai.async_block_till_done()

    expected_actions = []
    expected_actions += [
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
        (RegistryEntryHider.INTEGRATION, None),
        (RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_actions_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by,
    entity_category,
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
        supported_features=CoverEntityFeature.CLOSE,
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
        for action in ("close",)
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


async def test_get_action_capabilities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from a cover action."""
    ent = MockCover(
        name="Set position cover",
        unique_id="unique_set_pos_cover",
        current_cover_position=50,
        supported_features=CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT,
    )
    setup_test_component_platform(menuai, DOMAIN, [ent])
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

    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 5  # open, close, open_tilt, close_tilt
    action_types = {action["type"] for action in actions}
    assert action_types == {"open", "close", "stop", "open_tilt", "close_tilt"}
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == {"extra_fields": []}


async def test_get_action_capabilities_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from a cover action."""
    ent = MockCover(
        name="Set position cover",
        unique_id="unique_set_pos_cover",
        current_cover_position=50,
        supported_features=CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT,
    )
    setup_test_component_platform(menuai, DOMAIN, [ent])
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

    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 5  # open, close, open_tilt, close_tilt
    action_types = {action["type"] for action in actions}
    assert action_types == {"open", "close", "stop", "open_tilt", "close_tilt"}
    for action in actions:
        action["entity_id"] = entity_registry.async_get(action["entity_id"]).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == {"extra_fields": []}


async def test_get_action_capabilities_set_pos(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover action."""
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
                "name": "position",
                "optional": True,
                "type": "integer",
                "default": 0,
                "valueMax": 100,
                "valueMin": 0,
            }
        ]
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 4  # set_position, open, close, stop
    action_types = {action["type"] for action in actions}
    assert action_types == {"set_position", "open", "close", "stop"}
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        if action["type"] == "set_position":
            assert capabilities == expected_capabilities
        else:
            assert capabilities == {"extra_fields": []}


async def test_get_action_capabilities_set_tilt_pos(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test we get the expected capabilities from a cover action."""
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
                "name": "position",
                "optional": True,
                "type": "integer",
                "default": 0,
                "valueMax": 100,
                "valueMin": 0,
            }
        ]
    }
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 5
    action_types = {action["type"] for action in actions}
    assert action_types == {
        "open",
        "close",
        "set_tilt_position",
        "open_tilt",
        "close_tilt",
    }
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        if action["type"] == "set_tilt_position":
            assert capabilities == expected_capabilities
        else:
            assert capabilities == {"extra_fields": []}


async def test_action(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for cover actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_event_open"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "open",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_close"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "close",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_stop"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "stop",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    open_calls = async_mock_service(menuai, "cover", "open_cover")
    close_calls = async_mock_service(menuai, "cover", "close_cover")
    stop_calls = async_mock_service(menuai, "cover", "stop_cover")

    menuai.bus.async_fire("test_event_open")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 0
    assert len(stop_calls) == 0

    menuai.bus.async_fire("test_event_close")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 1
    assert len(stop_calls) == 0

    menuai.bus.async_fire("test_event_stop")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 1
    assert len(stop_calls) == 1

    assert open_calls[0].domain == DOMAIN
    assert open_calls[0].service == "open_cover"
    assert open_calls[0].data == {"entity_id": entry.entity_id}
    assert close_calls[0].domain == DOMAIN
    assert close_calls[0].service == "close_cover"
    assert close_calls[0].data == {"entity_id": entry.entity_id}
    assert stop_calls[0].domain == DOMAIN
    assert stop_calls[0].service == "stop_cover"
    assert stop_calls[0].data == {"entity_id": entry.entity_id}


async def test_action_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for cover actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_event_open"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "open",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    open_calls = async_mock_service(menuai, "cover", "open_cover")

    menuai.bus.async_fire("test_event_open")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1

    assert open_calls[0].domain == DOMAIN
    assert open_calls[0].service == "open_cover"
    assert open_calls[0].data == {"entity_id": entry.entity_id}


async def test_action_tilt(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for cover tilt actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_event_open"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "open_tilt",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_close"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "close_tilt",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    open_calls = async_mock_service(menuai, "cover", "open_cover_tilt")
    close_calls = async_mock_service(menuai, "cover", "close_cover_tilt")

    menuai.bus.async_fire("test_event_open")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 0

    menuai.bus.async_fire("test_event_close")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 1

    menuai.bus.async_fire("test_event_stop")
    await menuai.async_block_till_done()
    assert len(open_calls) == 1
    assert len(close_calls) == 1

    assert open_calls[0].domain == DOMAIN
    assert open_calls[0].service == "open_cover_tilt"
    assert open_calls[0].data == {"entity_id": entry.entity_id}
    assert close_calls[0].domain == DOMAIN
    assert close_calls[0].service == "close_cover_tilt"
    assert close_calls[0].data == {"entity_id": entry.entity_id}


async def test_action_set_position(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test for cover set position actions."""
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
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_set_pos",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "set_position",
                        "position": 25,
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_event_set_tilt_pos",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "set_tilt_position",
                        "position": 75,
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    cover_pos_calls = async_mock_service(menuai, "cover", "set_cover_position")
    tilt_pos_calls = async_mock_service(menuai, "cover", "set_cover_tilt_position")

    menuai.bus.async_fire("test_event_set_pos")
    await menuai.async_block_till_done()
    assert len(cover_pos_calls) == 1
    assert len(tilt_pos_calls) == 0

    menuai.bus.async_fire("test_event_set_tilt_pos")
    await menuai.async_block_till_done()
    assert len(cover_pos_calls) == 1
    assert len(tilt_pos_calls) == 1

    assert cover_pos_calls[0].domain == DOMAIN
    assert cover_pos_calls[0].service == "set_cover_position"
    assert cover_pos_calls[0].data == {"entity_id": entry.entity_id, "position": 25}
    assert tilt_pos_calls[0].domain == DOMAIN
    assert tilt_pos_calls[0].service == "set_cover_tilt_position"
    assert tilt_pos_calls[0].data == {"entity_id": entry.entity_id, "tilt_position": 75}
