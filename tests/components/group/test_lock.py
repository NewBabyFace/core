"""The tests for the Group Lock platform."""

from unittest.mock import patch

import pytest

from menuai import config as menuai_config
from menuai.components.demo import lock as demo_lock
from menuai.components.group import DOMAIN, SERVICE_RELOAD
from menuai.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
    LockState,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import get_fixture_path


async def test_default_state(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test lock group default state."""
    menuai.states.async_set("lock.front", "locked")
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["lock.front", "lock.back"],
                "name": "Door Group",
                "unique_id": "unique_identifier",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.door_group")
    assert state is not None
    assert state.state == LockState.LOCKED
    assert state.attributes.get(ATTR_ENTITY_ID) == ["lock.front", "lock.back"]

    entry = entity_registry.async_get("lock.door_group")
    assert entry
    assert entry.unique_id == "unique_identifier"


async def test_state_reporting(menuai: menuai) -> None:
    """Test the state reporting.

    The group state is unavailable if all group members are unavailable.
    Otherwise, the group state is unknown if at least one group member is unknown or unavailable.
    Otherwise, the group state is jammed if at least one group member is jammed.
    Otherwise, the group state is locking if at least one group member is locking.
    Otherwise, the group state is unlocking if at least one group member is unlocking.
    Otherwise, the group state is unlocked if at least one group member is unlocked.
    Otherwise, the group state is locked.
    """
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["lock.test1", "lock.test2"],
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    # Initial state with no group member in the state machine -> unavailable
    assert menuai.states.get("lock.lock_group").state == STATE_UNAVAILABLE

    # All group members unavailable -> unavailable
    menuai.states.async_set("lock.test1", STATE_UNAVAILABLE)
    menuai.states.async_set("lock.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("lock.lock_group").state == STATE_UNAVAILABLE

    # The group state is unknown if all group members are unknown or unavailable.
    for state_1 in (
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    ):
        menuai.states.async_set("lock.test1", state_1)
        menuai.states.async_set("lock.test2", STATE_UNKNOWN)
        await menuai.async_block_till_done()
        assert menuai.states.get("lock.lock_group").state == STATE_UNKNOWN

    # At least one member jammed -> group jammed
    for state_1 in (
        LockState.JAMMED,
        LockState.LOCKED,
        LockState.LOCKING,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
        LockState.UNLOCKED,
        LockState.UNLOCKING,
    ):
        menuai.states.async_set("lock.test1", state_1)
        menuai.states.async_set("lock.test2", LockState.JAMMED)
        await menuai.async_block_till_done()
        assert menuai.states.get("lock.lock_group").state == LockState.JAMMED

    # At least one member locking -> group unlocking
    for state_1 in (
        LockState.LOCKED,
        LockState.LOCKING,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
        LockState.UNLOCKED,
        LockState.UNLOCKING,
    ):
        menuai.states.async_set("lock.test1", state_1)
        menuai.states.async_set("lock.test2", LockState.LOCKING)
        await menuai.async_block_till_done()
        assert menuai.states.get("lock.lock_group").state == LockState.LOCKING

    # At least one member unlocking -> group unlocking
    for state_1 in (
        LockState.LOCKED,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
        LockState.UNLOCKED,
        LockState.UNLOCKING,
    ):
        menuai.states.async_set("lock.test1", state_1)
        menuai.states.async_set("lock.test2", LockState.UNLOCKING)
        await menuai.async_block_till_done()
        assert menuai.states.get("lock.lock_group").state == LockState.UNLOCKING

    # At least one member unlocked -> group unlocked
    for state_1 in (
        LockState.LOCKED,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
        LockState.UNLOCKED,
    ):
        menuai.states.async_set("lock.test1", state_1)
        menuai.states.async_set("lock.test2", LockState.UNLOCKED)
        await menuai.async_block_till_done()
        assert menuai.states.get("lock.lock_group").state == LockState.UNLOCKED

    # Otherwise -> locked
    menuai.states.async_set("lock.test1", LockState.LOCKED)
    menuai.states.async_set("lock.test2", LockState.LOCKED)
    await menuai.async_block_till_done()
    assert menuai.states.get("lock.lock_group").state == LockState.LOCKED

    # All group members removed from the state machine -> unavailable
    menuai.states.async_remove("lock.test1")
    menuai.states.async_remove("lock.test2")
    await menuai.async_block_till_done()
    assert menuai.states.get("lock.lock_group").state == STATE_UNAVAILABLE


async def test_service_calls_openable(menuai: menuai) -> None:
    """Test service calls with open support."""
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: [
                {"platform": "kitchen_sink"},
                {
                    "platform": DOMAIN,
                    "entities": [
                        "lock.openable_lock",
                        "lock.another_openable_lock",
                    ],
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    group_state = menuai.states.get("lock.lock_group")
    assert group_state.state == LockState.UNLOCKED
    assert menuai.states.get("lock.openable_lock").state == LockState.LOCKED
    assert menuai.states.get("lock.another_openable_lock").state == LockState.UNLOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_OPEN,
        {ATTR_ENTITY_ID: "lock.lock_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.openable_lock").state == LockState.OPEN
    assert menuai.states.get("lock.another_openable_lock").state == LockState.OPEN

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.lock_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.openable_lock").state == LockState.LOCKED
    assert menuai.states.get("lock.another_openable_lock").state == LockState.LOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "lock.lock_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.openable_lock").state == LockState.UNLOCKED
    assert menuai.states.get("lock.another_openable_lock").state == LockState.UNLOCKED


async def test_service_calls_basic(menuai: menuai) -> None:
    """Test service calls without open support."""
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: [
                {"platform": "kitchen_sink"},
                {
                    "platform": DOMAIN,
                    "entities": [
                        "lock.basic_lock",
                        "lock.another_basic_lock",
                    ],
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    group_state = menuai.states.get("lock.lock_group")
    assert group_state.state == LockState.UNLOCKED
    assert menuai.states.get("lock.basic_lock").state == LockState.LOCKED
    assert menuai.states.get("lock.another_basic_lock").state == LockState.UNLOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.lock_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.basic_lock").state == LockState.LOCKED
    assert menuai.states.get("lock.another_basic_lock").state == LockState.LOCKED

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "lock.lock_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.basic_lock").state == LockState.UNLOCKED
    assert menuai.states.get("lock.another_basic_lock").state == LockState.UNLOCKED

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_OPEN,
            {ATTR_ENTITY_ID: "lock.lock_group"},
            blocking=True,
        )


async def test_reload(menuai: menuai) -> None:
    """Test the ability to reload locks."""
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: [
                {"platform": "demo"},
                {
                    "platform": DOMAIN,
                    "entities": [
                        "lock.front_door",
                        "lock.kitchen_door",
                    ],
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get("lock.lock_group").state == LockState.UNLOCKED

    yaml_path = get_fixture_path("configuration.yaml", "group")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert menuai.states.get("lock.lock_group") is None
    assert menuai.states.get("lock.inside_locks_g") is not None
    assert menuai.states.get("lock.outside_locks_g") is not None


async def test_reload_with_platform_not_setup(menuai: menuai) -> None:
    """Test the ability to reload locks."""
    menuai.states.async_set("lock.something", LockState.UNLOCKED)
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: [
                {"platform": "demo"},
            ]
        },
    )
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "lock.something", "icon": "mdi:work"},
            }
        },
    )
    await menuai.async_block_till_done()

    yaml_path = get_fixture_path("configuration.yaml", "group")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert menuai.states.get("lock.lock_group") is None
    assert menuai.states.get("lock.inside_locks_g") is not None
    assert menuai.states.get("lock.outside_locks_g") is not None


async def test_reload_with_base_integration_platform_not_setup(
    menuai: menuai,
) -> None:
    """Test the ability to reload locks."""
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "lock.something", "icon": "mdi:work"},
            }
        },
    )
    await menuai.async_block_till_done()
    menuai.states.async_set("lock.front_lock", LockState.LOCKED)
    menuai.states.async_set("lock.back_lock", LockState.UNLOCKED)

    menuai.states.async_set("lock.outside_lock", LockState.LOCKED)
    menuai.states.async_set("lock.outside_lock_2", LockState.LOCKED)

    yaml_path = get_fixture_path("configuration.yaml", "group")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert menuai.states.get("lock.lock_group") is None
    assert menuai.states.get("lock.inside_locks_g") is not None
    assert menuai.states.get("lock.outside_locks_g") is not None
    assert menuai.states.get("lock.inside_locks_g").state == LockState.UNLOCKED
    assert menuai.states.get("lock.outside_locks_g").state == LockState.LOCKED


@patch.object(demo_lock, "LOCK_UNLOCK_DELAY", 0)
async def test_nested_group(menuai: menuai) -> None:
    """Test nested lock group."""
    await async_setup_component(
        menuai,
        LOCK_DOMAIN,
        {
            LOCK_DOMAIN: [
                {"platform": "demo"},
                {
                    "platform": DOMAIN,
                    "entities": ["lock.some_group"],
                    "name": "Nested Group",
                },
                {
                    "platform": DOMAIN,
                    "entities": [
                        "lock.front_door",
                        "lock.kitchen_door",
                    ],
                    "name": "Some Group",
                },
            ]
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.some_group")
    assert state is not None
    assert state.state == LockState.UNLOCKED
    assert state.attributes.get(ATTR_ENTITY_ID) == [
        "lock.front_door",
        "lock.kitchen_door",
    ]

    state = menuai.states.get("lock.nested_group")
    assert state is not None
    assert state.state == LockState.UNLOCKED
    assert state.attributes.get(ATTR_ENTITY_ID) == ["lock.some_group"]

    # Test controlling the nested group
    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.nested_group"},
        blocking=True,
    )
    assert menuai.states.get("lock.front_door").state == LockState.LOCKED
    assert menuai.states.get("lock.kitchen_door").state == LockState.LOCKED
    assert menuai.states.get("lock.some_group").state == LockState.LOCKED
    assert menuai.states.get("lock.nested_group").state == LockState.LOCKED
