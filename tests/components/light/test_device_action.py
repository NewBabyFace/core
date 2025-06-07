"""The test for light device automation."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.light import (
    ATTR_SUPPORTED_COLOR_MODES,
    DOMAIN,
    FLASH_LONG,
    FLASH_SHORT,
    ColorMode,
    LightEntityFeature,
)
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_get_device_automation_capabilities,
    async_get_device_automations,
    async_mock_service,
)


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


async def test_get_actions(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected actions from a light."""
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
        supported_features=LightEntityFeature.FLASH,
        capabilities={"supported_color_modes": ["brightness"]},
    )
    expected_actions = [
        {
            "domain": DOMAIN,
            "type": action,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for action in (
            "brightness_decrease",
            "brightness_increase",
            "flash",
            "turn_off",
            "turn_on",
            "toggle",
        )
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
        supported_features=0,
        capabilities={"supported_color_modes": ["onoff"]},
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
        for action in ("turn_on", "turn_off", "toggle")
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
    """Test we get the expected capabilities from a light action."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    # Test with entity without optional capabilities
    entity_id = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
    ).entity_id
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == 3
    action_types = {action["type"] for action in actions}
    assert action_types == {"turn_on", "toggle", "turn_off"}
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities == {"extra_fields": []}

    # Test without entity
    entity_registry.async_remove(entity_id)
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        assert capabilities in ({"extra_fields": []}, {})


@pytest.mark.parametrize(
    (
        "set_state",
        "expected_actions",
        "supported_features_reg",
        "supported_features_state",
        "capabilities_reg",
        "attributes_state",
        "expected_capabilities",
    ),
    [
        (
            False,
            {
                "turn_on",
                "toggle",
                "turn_off",
                "brightness_increase",
                "brightness_decrease",
            },
            0,
            0,
            {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS]},
            {},
            {
                "turn_on": [
                    {
                        "name": "brightness_pct",
                        "optional": True,
                        "type": "float",
                        "valueMax": 100,
                        "valueMin": 0,
                    }
                ]
            },
        ),
        (
            True,
            {
                "turn_on",
                "toggle",
                "turn_off",
                "brightness_increase",
                "brightness_decrease",
            },
            0,
            0,
            None,
            {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS]},
            {
                "turn_on": [
                    {
                        "name": "brightness_pct",
                        "optional": True,
                        "type": "float",
                        "valueMax": 100,
                        "valueMin": 0,
                    }
                ]
            },
        ),
        (
            False,
            {"turn_on", "toggle", "turn_off", "flash"},
            LightEntityFeature.FLASH,
            0,
            None,
            {},
            {
                "turn_on": [
                    {
                        "name": "flash",
                        "optional": True,
                        "type": "select",
                        "options": [("short", "short"), ("long", "long")],
                    }
                ]
            },
        ),
        (
            True,
            {"turn_on", "toggle", "turn_off", "flash"},
            0,
            LightEntityFeature.FLASH,
            None,
            {},
            {
                "turn_on": [
                    {
                        "name": "flash",
                        "optional": True,
                        "type": "select",
                        "options": [("short", "short"), ("long", "long")],
                    }
                ]
            },
        ),
    ],
)
async def test_get_action_capabilities_features(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state,
    expected_actions,
    supported_features_reg,
    supported_features_state,
    capabilities_reg,
    attributes_state,
    expected_capabilities,
) -> None:
    """Test we get the expected capabilities from a light action."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_id = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        supported_features=supported_features_reg,
        capabilities=capabilities_reg,
    ).entity_id
    if set_state:
        menuai.states.async_set(
            entity_id,
            None,
            {"supported_features": supported_features_state, **attributes_state},
        )

    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == len(expected_actions)
    action_types = {action["type"] for action in actions}
    assert action_types == expected_actions
    for action in actions:
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        expected = {"extra_fields": expected_capabilities.get(action["type"], [])}
        assert capabilities == expected


@pytest.mark.parametrize(
    (
        "set_state",
        "expected_actions",
        "supported_features_reg",
        "supported_features_state",
        "capabilities_reg",
        "attributes_state",
        "expected_capabilities",
    ),
    [
        (
            False,
            {
                "turn_on",
                "toggle",
                "turn_off",
                "brightness_increase",
                "brightness_decrease",
            },
            0,
            0,
            {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS]},
            {},
            {
                "turn_on": [
                    {
                        "name": "brightness_pct",
                        "optional": True,
                        "type": "float",
                        "valueMax": 100,
                        "valueMin": 0,
                    }
                ]
            },
        ),
        (
            True,
            {
                "turn_on",
                "toggle",
                "turn_off",
                "brightness_increase",
                "brightness_decrease",
            },
            0,
            0,
            None,
            {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.BRIGHTNESS]},
            {
                "turn_on": [
                    {
                        "name": "brightness_pct",
                        "optional": True,
                        "type": "float",
                        "valueMax": 100,
                        "valueMin": 0,
                    }
                ]
            },
        ),
        (
            False,
            {"turn_on", "toggle", "turn_off", "flash"},
            LightEntityFeature.FLASH,
            0,
            None,
            {},
            {
                "turn_on": [
                    {
                        "name": "flash",
                        "optional": True,
                        "type": "select",
                        "options": [("short", "short"), ("long", "long")],
                    }
                ]
            },
        ),
        (
            True,
            {"turn_on", "toggle", "turn_off", "flash"},
            0,
            LightEntityFeature.FLASH,
            None,
            {},
            {
                "turn_on": [
                    {
                        "name": "flash",
                        "optional": True,
                        "type": "select",
                        "options": [("short", "short"), ("long", "long")],
                    }
                ]
            },
        ),
    ],
)
async def test_get_action_capabilities_features_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    set_state,
    expected_actions,
    supported_features_reg,
    supported_features_state,
    capabilities_reg,
    attributes_state,
    expected_capabilities,
) -> None:
    """Test we get the expected capabilities from a light action."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_id = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        supported_features=supported_features_reg,
        capabilities=capabilities_reg,
    ).entity_id
    if set_state:
        menuai.states.async_set(
            entity_id,
            None,
            {"supported_features": supported_features_state, **attributes_state},
        )

    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert len(actions) == len(expected_actions)
    action_types = {action["type"] for action in actions}
    assert action_types == expected_actions
    for action in actions:
        action["entity_id"] = entity_registry.async_get(action["entity_id"]).entity_id
        capabilities = await async_get_device_automation_capabilities(
            menuai, DeviceAutomationType.ACTION, action
        )
        expected = {"extra_fields": expected_capabilities.get(action["type"], [])}
        assert capabilities == expected


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_action(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for turn_on and turn_off actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_off"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "turn_off",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_on"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "turn_on",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_toggle"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "toggle",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_flash_short"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "flash",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_flash_long"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "flash",
                        "flash": "long",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_brightness_increase",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "brightness_increase",
                    },
                },
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_brightness_decrease",
                    },
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "brightness_decrease",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_brightness"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "turn_on",
                        "brightness_pct": 75,
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    turn_on_calls = async_mock_service(menuai, DOMAIN, "turn_on")
    turn_off_calls = async_mock_service(menuai, DOMAIN, "turn_off")
    toggle_calls = async_mock_service(menuai, DOMAIN, "toggle")

    menuai.bus.async_fire("test_toggle")
    await menuai.async_block_till_done()
    assert len(toggle_calls) == 1
    assert toggle_calls[-1].data == {"entity_id": entry.entity_id}

    menuai.bus.async_fire("test_off")
    await menuai.async_block_till_done()
    assert len(turn_off_calls) == 1
    assert turn_off_calls[-1].data == {"entity_id": entry.entity_id}

    menuai.bus.async_fire("test_brightness_increase")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 1
    assert turn_on_calls[-1].data == {
        "entity_id": entry.entity_id,
        "brightness_step_pct": 10,
    }

    menuai.bus.async_fire("test_brightness_decrease")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 2
    assert turn_on_calls[-1].data == {
        "entity_id": entry.entity_id,
        "brightness_step_pct": -10,
    }

    menuai.bus.async_fire("test_brightness")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 3
    assert turn_on_calls[-1].data == {
        "entity_id": entry.entity_id,
        "brightness_pct": 75,
    }

    menuai.bus.async_fire("test_on")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 4
    assert turn_on_calls[-1].data == {"entity_id": entry.entity_id}

    menuai.bus.async_fire("test_flash_short")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 5
    assert turn_on_calls[-1].data == {
        "entity_id": entry.entity_id,
        "flash": FLASH_SHORT,
    }

    menuai.bus.async_fire("test_flash_long")
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 6
    assert turn_on_calls[-1].data == {"entity_id": entry.entity_id, "flash": FLASH_LONG}


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_action_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for turn_on and turn_off actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_off"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.entity_id,
                        "type": "turn_off",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    turn_off_calls = async_mock_service(menuai, DOMAIN, "turn_off")

    menuai.bus.async_fire("test_off")
    await menuai.async_block_till_done()
    assert len(turn_off_calls) == 1
    assert turn_off_calls[-1].data == {"entity_id": entry.entity_id}
