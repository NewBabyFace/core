"""The tests for Lock device actions."""

import pytest
from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.lock import DOMAIN, LockEntityFeature
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_get_device_automations,
    async_mock_service,
)


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.mark.parametrize(
    ("set_state", "features_reg", "features_state", "expected_action_types"),
    [
        (False, 0, 0, []),
        (False, LockEntityFeature.OPEN, 0, ["open"]),
        (True, 0, 0, []),
        (True, 0, LockEntityFeature.OPEN, ["open"]),
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
    """Test we get the expected actions from a lock."""
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
    expected_actions = []
    basic_action_types = ["lock", "unlock"]
    expected_actions += [
        {
            "domain": DOMAIN,
            "type": action,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for action in basic_action_types
    ]
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
        supported_features=0,
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
        for action in ("lock", "unlock")
    ]
    actions = await async_get_device_automations(
        menuai, DeviceAutomationType.ACTION, device_entry.id
    )
    assert actions == unordered(expected_actions)


async def test_action(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for lock actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_event_lock"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "lock",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_unlock"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "unlock",
                    },
                },
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

    lock_calls = async_mock_service(menuai, "lock", "lock")
    unlock_calls = async_mock_service(menuai, "lock", "unlock")
    open_calls = async_mock_service(menuai, "lock", "open")

    menuai.bus.async_fire("test_event_lock")
    await menuai.async_block_till_done()
    assert len(lock_calls) == 1
    assert len(unlock_calls) == 0
    assert len(open_calls) == 0

    menuai.bus.async_fire("test_event_unlock")
    await menuai.async_block_till_done()
    assert len(lock_calls) == 1
    assert len(unlock_calls) == 1
    assert len(open_calls) == 0

    menuai.bus.async_fire("test_event_open")
    await menuai.async_block_till_done()
    assert len(lock_calls) == 1
    assert len(unlock_calls) == 1
    assert len(open_calls) == 1

    assert lock_calls[0].domain == DOMAIN
    assert lock_calls[0].service == "lock"
    assert lock_calls[0].data == {"entity_id": entry.entity_id}
    assert unlock_calls[0].domain == DOMAIN
    assert unlock_calls[0].service == "unlock"
    assert unlock_calls[0].data == {"entity_id": entry.entity_id}
    assert open_calls[0].domain == DOMAIN
    assert open_calls[0].service == "open"
    assert open_calls[0].data == {"entity_id": entry.entity_id}


async def test_action_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for lock actions."""
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
                    "trigger": {"platform": "event", "event_type": "test_event_lock"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "lock",
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    lock_calls = async_mock_service(menuai, "lock", "lock")

    menuai.bus.async_fire("test_event_lock")
    await menuai.async_block_till_done()
    assert len(lock_calls) == 1

    assert lock_calls[0].domain == DOMAIN
    assert lock_calls[0].service == "lock"
    assert lock_calls[0].data == {"entity_id": entry.entity_id}
