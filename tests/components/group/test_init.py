"""The tests for the Group components."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import group
from menuai.components.group.registry import GroupIntegrationRegistry
from menuai.components.lock import LockState
from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    EVENT_menuai_START,
    SERVICE_RELOAD,
    STATE_CLOSED,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from menuai.core import CoreState, menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from . import common

from tests.common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    assert_setup_component,
    mock_integration,
    mock_platform,
)


async def help_test_mixed_entity_platforms_on_off_state_test(
    menuai: menuai,
    on_off_states1: tuple[set[str], str, str],
    on_off_states2: tuple[set[str], str, str],
    entity_and_state1_state_2: tuple[str, str | None, str | None],
    group_state1: str,
    group_state2: str,
    grouped_groups: bool = False,
) -> None:
    """Help test on_off_states on mixed entity platforms."""

    class MockGroupPlatform1(MockPlatform):
        """Mock a group platform module for test1 integration."""

        def async_describe_on_off_states(
            self, menuai: menuai, registry: GroupIntegrationRegistry
        ) -> None:
            """Describe group on off states."""
            registry.on_off_states("test1", *on_off_states1)

    class MockGroupPlatform2(MockPlatform):
        """Mock a group platform module for test2 integration."""

        def async_describe_on_off_states(
            self, menuai: menuai, registry: GroupIntegrationRegistry
        ) -> None:
            """Describe group on off states."""
            registry.on_off_states("test2", *on_off_states2)

    mock_integration(menuai, MockModule(domain="test1"))
    mock_platform(menuai, "test1.group", MockGroupPlatform1())
    assert await async_setup_component(menuai, "test1", {"test1": {}})

    mock_integration(menuai, MockModule(domain="test2"))
    mock_platform(menuai, "test2.group", MockGroupPlatform2())
    assert await async_setup_component(menuai, "test2", {"test2": {}})

    if grouped_groups:
        assert await async_setup_component(
            menuai,
            "group",
            {
                "group": {
                    "test1": {
                        "entities": [
                            item[0]
                            for item in entity_and_state1_state_2
                            if item[0].startswith("test1.")
                        ]
                    },
                    "test2": {
                        "entities": [
                            item[0]
                            for item in entity_and_state1_state_2
                            if item[0].startswith("test2.")
                        ]
                    },
                    "test": {"entities": ["group.test1", "group.test2"]},
                }
            },
        )
    else:
        assert await async_setup_component(
            menuai,
            "group",
            {
                "group": {
                    "test": {
                        "entities": [item[0] for item in entity_and_state1_state_2]
                    },
                }
            },
        )
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("group.test")
    assert state is not None

    # Set first state
    for entity_id, state1, _ in entity_and_state1_state_2:
        menuai.states.async_set(entity_id, state1)

    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("group.test")
    assert state is not None
    assert state.state == group_state1

    # Set second state
    for entity_id, _, state2 in entity_and_state1_state_2:
        menuai.states.async_set(entity_id, state2)

    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get("group.test")
    assert state is not None
    assert state.state == group_state2


async def test_setup_group_with_mixed_groupable_states(menuai: menuai) -> None:
    """Try to set up a group with mixed groupable states."""

    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("device_tracker.Paulus", STATE_HOME)

    assert await async_setup_component(menuai, "group", {})

    await group.Group.async_create_group(
        menuai,
        "person_and_light",
        created_by_service=False,
        entity_ids=["light.Bowl", "device_tracker.Paulus"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    await menuai.async_block_till_done()

    assert menuai.states.get(f"{group.DOMAIN}.person_and_light").state == STATE_ON


async def test_setup_group_with_a_non_existing_state(menuai: menuai) -> None:
    """Try to set up a group with a non existing state."""
    menuai.states.async_set("light.Bowl", STATE_ON)

    assert await async_setup_component(menuai, "group", {})

    grp = await group.Group.async_create_group(
        menuai,
        "light_and_nothing",
        created_by_service=False,
        entity_ids=["light.Bowl", "non.existing"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert grp.state == STATE_ON


async def test_setup_group_with_non_groupable_states(menuai: menuai) -> None:
    """Test setup with groups which are not groupable."""
    menuai.states.async_set("cast.living_room", "Plex")
    menuai.states.async_set("cast.bedroom", "Netflix")

    assert await async_setup_component(menuai, "group", {})

    grp = await group.Group.async_create_group(
        menuai,
        "chromecasts",
        created_by_service=False,
        entity_ids=["cast.living_room", "cast.bedroom"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert grp.state is None


async def test_setup_empty_group(menuai: menuai) -> None:
    """Try to set up an empty group."""
    grp = await group.Group.async_create_group(
        menuai,
        "nothing",
        created_by_service=False,
        entity_ids=[],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert grp.state is None


async def test_monitor_group(menuai: menuai) -> None:
    """Test if the group keeps track of states."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    # Test if group setup in our init mode is ok
    assert test_group.entity_id in menuai.states.async_entity_ids()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_ON
    assert group_state.attributes.get(group.ATTR_AUTO)


async def test_group_turns_off_if_all_off(menuai: menuai) -> None:
    """Test if turn off if the last device that was on turns off."""
    menuai.states.async_set("light.Bowl", STATE_OFF)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_OFF


async def test_group_turns_on_if_all_are_off_and_one_turns_on(
    menuai: menuai,
) -> None:
    """Test if turn on if all devices were turned off and one turns on."""
    menuai.states.async_set("light.Bowl", STATE_OFF)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    # Turn one on
    menuai.states.async_set("light.Ceiling", STATE_ON)
    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_ON


async def test_allgroup_stays_off_if_all_are_off_and_one_turns_on(
    menuai: menuai,
) -> None:
    """Group with all: true, stay off if one device turns on."""
    menuai.states.async_set("light.Bowl", STATE_OFF)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=True,
        object_id=None,
        order=None,
    )

    # Turn one on
    menuai.states.async_set("light.Ceiling", STATE_ON)
    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_OFF


async def test_allgroup_turn_on_if_last_turns_on(menuai: menuai) -> None:
    """Group with all: true, turn on if all devices are on."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=True,
        object_id=None,
        order=None,
    )

    # Turn one on
    menuai.states.async_set("light.Ceiling", STATE_ON)
    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_ON


async def test_expand_entity_ids(menuai: menuai) -> None:
    """Test expand_entity_ids method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert sorted(["light.ceiling", "light.bowl"]) == sorted(
        group.expand_entity_ids(menuai, [test_group.entity_id])
    )


async def test_expand_entity_ids_does_not_return_duplicates(
    menuai: menuai,
) -> None:
    """Test that expand_entity_ids does not return duplicates."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert sorted(
        group.expand_entity_ids(menuai, [test_group.entity_id, "light.Ceiling"])
    ) == ["light.bowl", "light.ceiling"]

    assert sorted(
        group.expand_entity_ids(menuai, ["light.bowl", test_group.entity_id])
    ) == ["light.bowl", "light.ceiling"]


async def test_expand_entity_ids_recursive(menuai: menuai) -> None:
    """Test expand_entity_ids method with a group that contains itself."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling", "group.init_group"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert sorted(["light.ceiling", "light.bowl"]) == sorted(
        group.expand_entity_ids(menuai, [test_group.entity_id])
    )


async def test_expand_entity_ids_ignores_non_strings(menuai: menuai) -> None:
    """Test that non string elements in lists are ignored."""
    assert group.expand_entity_ids(menuai, [5, True]) == []


async def test_get_entity_ids(menuai: menuai) -> None:
    """Test get_entity_ids method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert sorted(group.get_entity_ids(menuai, test_group.entity_id)) == [
        "light.bowl",
        "light.ceiling",
    ]


async def test_get_entity_ids_with_domain_filter(menuai: menuai) -> None:
    """Test if get_entity_ids works with a domain_filter."""
    menuai.states.async_set("switch.AC", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    mixed_group = await group.Group.async_create_group(
        menuai,
        "mixed_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "switch.AC"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert group.get_entity_ids(
        menuai, mixed_group.entity_id, domain_filter="switch"
    ) == ["switch.ac"]


async def test_get_entity_ids_with_non_existing_group_name(menuai: menuai) -> None:
    """Test get_entity_ids with a non existing group."""
    assert group.get_entity_ids(menuai, "non_existing") == []


async def test_get_entity_ids_with_non_group_state(menuai: menuai) -> None:
    """Test get_entity_ids with a non group state."""
    assert group.get_entity_ids(menuai, "switch.AC") == []


async def test_group_being_init_before_first_tracked_state_is_set_to_on(
    menuai: menuai,
) -> None:
    """Test if the groups turn on.

    If no states existed and now a state it is tracking is being added
    as ON.
    """

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "test group",
        created_by_service=False,
        entity_ids=["light.not_there_1"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    menuai.states.async_set("light.not_there_1", STATE_ON)

    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_ON


async def test_group_being_init_before_first_tracked_state_is_set_to_off(
    menuai: menuai,
) -> None:
    """Test if the group turns off.

    If no states existed and now a state it is tracking is being added
    as OFF.
    """
    assert await async_setup_component(menuai, "group", {})
    test_group = await group.Group.async_create_group(
        menuai,
        "test group",
        created_by_service=False,
        entity_ids=["light.not_there_1"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    menuai.states.async_set("light.not_there_1", STATE_OFF)

    await menuai.async_block_till_done()

    group_state = menuai.states.get(test_group.entity_id)
    assert group_state.state == STATE_OFF


async def test_groups_get_unique_names(menuai: menuai) -> None:
    """Two groups with same name should both have a unique entity id."""

    assert await async_setup_component(menuai, "group", {})

    grp1 = await group.Group.async_create_group(
        menuai,
        "Je suis Charlie",
        created_by_service=False,
        entity_ids=None,
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    grp2 = await group.Group.async_create_group(
        menuai,
        "Je suis Charlie",
        created_by_service=False,
        entity_ids=None,
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert grp1.entity_id != grp2.entity_id


async def test_expand_entity_ids_expands_nested_groups(menuai: menuai) -> None:
    """Test if entity ids epands to nested groups."""

    assert await async_setup_component(menuai, "group", {})

    await group.Group.async_create_group(
        menuai,
        "light",
        created_by_service=False,
        entity_ids=["light.test_1", "light.test_2"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    await group.Group.async_create_group(
        menuai,
        "switch",
        created_by_service=False,
        entity_ids=["switch.test_1", "switch.test_2"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    await group.Group.async_create_group(
        menuai,
        "group_of_groups",
        created_by_service=False,
        entity_ids=["group.light", "group.switch"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert sorted(group.expand_entity_ids(menuai, ["group.group_of_groups"])) == [
        "light.test_1",
        "light.test_2",
        "switch.test_1",
        "switch.test_2",
    ]


async def test_set_assumed_state_based_on_tracked(menuai: menuai) -> None:
    """Test assumed state."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert await async_setup_component(menuai, "group", {})

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=False,
        entity_ids=["light.Bowl", "light.Ceiling", "sensor.no_exist"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    state = menuai.states.get(test_group.entity_id)
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    menuai.states.async_set("light.Bowl", STATE_ON, {ATTR_ASSUMED_STATE: True})
    await menuai.async_block_till_done()

    state = menuai.states.get(test_group.entity_id)
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    menuai.states.async_set("light.Bowl", STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(test_group.entity_id)
    assert not state.attributes.get(ATTR_ASSUMED_STATE)


async def test_group_updated_after_device_tracker_zone_change(
    menuai: menuai,
) -> None:
    """Test group state when device tracker in group changes zone."""
    menuai.states.async_set("device_tracker.Adam", STATE_HOME)
    menuai.states.async_set("device_tracker.Eve", STATE_NOT_HOME)
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "group", {})
    assert await async_setup_component(menuai, "device_tracker", {})
    await menuai.async_block_till_done()

    await group.Group.async_create_group(
        menuai,
        "peeps",
        created_by_service=False,
        entity_ids=["device_tracker.Adam", "device_tracker.Eve"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    menuai.states.async_set("device_tracker.Adam", "cool_state_not_home")
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{group.DOMAIN}.peeps").state == STATE_NOT_HOME


async def test_is_on(menuai: menuai) -> None:
    """Test is_on method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    assert group.is_on(menuai, "group.none") is False
    assert await async_setup_component(menuai, "light", {})
    assert await async_setup_component(menuai, "group", {})
    await menuai.async_block_till_done()

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    await menuai.async_block_till_done()

    assert group.is_on(menuai, test_group.entity_id) is True
    menuai.states.async_set("light.Bowl", STATE_OFF)
    await menuai.async_block_till_done()
    assert group.is_on(menuai, test_group.entity_id) is False

    # Try on non existing state
    assert not group.is_on(menuai, "non.existing")


@pytest.mark.parametrize(
    (
        "domains",
        "states_old",
        "states_new",
        "state_ison_group_old",
        "state_ison_group_new",
    ),
    [
        (
            ("light", "light"),
            (STATE_ON, STATE_OFF),
            (STATE_OFF, STATE_OFF),
            (STATE_ON, True),
            (STATE_OFF, False),
        ),
        (
            ("cover", "cover"),
            (LockState.OPEN, STATE_CLOSED),
            (STATE_CLOSED, STATE_CLOSED),
            (LockState.OPEN, True),
            (STATE_CLOSED, False),
        ),
        (
            ("lock", "lock"),
            (LockState.UNLOCKED, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.UNLOCKED, True),
            (LockState.LOCKED, False),
        ),
        (
            ("cover", "lock"),
            (LockState.OPEN, LockState.LOCKED),
            (STATE_CLOSED, LockState.LOCKED),
            (STATE_ON, True),
            (STATE_OFF, False),
        ),
        (
            ("cover", "lock"),
            (LockState.OPEN, LockState.UNLOCKED),
            (STATE_CLOSED, LockState.LOCKED),
            (STATE_ON, True),
            (STATE_OFF, False),
        ),
        (
            ("cover", "lock", "light"),
            (LockState.OPEN, LockState.LOCKED, STATE_ON),
            (STATE_CLOSED, LockState.LOCKED, STATE_OFF),
            (STATE_ON, True),
            (STATE_OFF, False),
        ),
        (
            ("lock", "lock"),
            (LockState.OPEN, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.UNLOCKED, True),
            (LockState.LOCKED, False),
        ),
        (
            ("lock", "lock"),
            (LockState.OPENING, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.UNLOCKED, True),
            (LockState.LOCKED, False),
        ),
        (
            ("lock", "lock"),
            (LockState.UNLOCKING, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.UNLOCKED, True),
            (LockState.LOCKED, False),
        ),
        (
            ("lock", "lock"),
            (LockState.LOCKING, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.UNLOCKED, True),
            (LockState.LOCKED, False),
        ),
        (
            ("lock", "lock"),
            (LockState.JAMMED, LockState.LOCKED),
            (LockState.LOCKED, LockState.LOCKED),
            (LockState.LOCKED, False),
            (LockState.LOCKED, False),
        ),
        (
            ("cover", "lock"),
            (LockState.OPEN, LockState.OPEN),
            (STATE_CLOSED, LockState.LOCKED),
            (STATE_ON, True),
            (STATE_OFF, False),
        ),
    ],
)
async def test_is_on_and_state_mixed_domains(
    menuai: menuai,
    domains: tuple[str, ...],
    states_old: tuple[str, ...],
    states_new: tuple[str, ...],
    state_ison_group_old: tuple[str, bool],
    state_ison_group_new: tuple[str, bool],
) -> None:
    """Test is_on method with mixed domains."""
    count = len(domains)
    entity_ids = [f"{domains[index]}.test_{index}" for index in range(count)]
    for index in range(count):
        menuai.states.async_set(entity_ids[index], states_old[index])

    assert not group.is_on(menuai, "group.none")
    await asyncio.gather(
        *[async_setup_component(menuai, domain, {}) for domain in set(domains)]
    )
    assert await async_setup_component(menuai, "group", {})
    await menuai.async_block_till_done()

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=entity_ids,
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    await menuai.async_block_till_done()

    # Assert on old state
    state = menuai.states.get(test_group.entity_id)
    assert state is not None
    assert state.state == state_ison_group_old[0]
    assert group.is_on(menuai, test_group.entity_id) == state_ison_group_old[1]

    # Switch and assert on new state
    for index in range(count):
        menuai.states.async_set(entity_ids[index], states_new[index])
    await menuai.async_block_till_done()
    state = menuai.states.get(test_group.entity_id)
    assert state is not None
    assert state.state == state_ison_group_new[0]
    assert group.is_on(menuai, test_group.entity_id) == state_ison_group_new[1]


async def test_reloading_groups(menuai: menuai) -> None:
    """Test reloading the group config."""
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "second_group": {"entities": "light.Bowl", "icon": "mdi:work"},
                "test_group": "hello.world,sensor.happy",
                "empty_group": {"name": "Empty Group", "entities": None},
            }
        },
    )
    await menuai.async_block_till_done()

    await group.Group.async_create_group(
        menuai,
        "all tests",
        created_by_service=True,
        entity_ids=["test.one", "test.two"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids()) == [
        "group.all_tests",
        "group.empty_group",
        "group.second_group",
        "group.test_group",
    ]
    assert menuai.bus.async_listeners()["state_changed"] == 1

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={
            "group": {"hello": {"entities": "light.Bowl", "icon": "mdi:work"}}
        },
    ):
        await menuai.services.async_call(group.DOMAIN, SERVICE_RELOAD)
        await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids()) == [
        "group.all_tests",
        "group.hello",
    ]
    assert menuai.bus.async_listeners()["state_changed"] == 1


async def test_modify_group(menuai: menuai) -> None:
    """Test modifying a group."""
    group_conf = OrderedDict()
    group_conf["modify_group"] = {
        "name": "friendly_name",
        "icon": "mdi:work",
        "entities": None,
    }

    assert await async_setup_component(menuai, "group", {"group": group_conf})
    await menuai.async_block_till_done()
    assert menuai.states.get(f"{group.DOMAIN}.modify_group")

    # The old way would create a new group modify_group1 because
    # internally it didn't know anything about those created in the config
    common.async_set_group(menuai, "modify_group", icon="mdi:play")
    await menuai.async_block_till_done()

    group_state = menuai.states.get(f"{group.DOMAIN}.modify_group")
    assert group_state

    assert menuai.states.async_entity_ids() == ["group.modify_group"]
    assert group_state.attributes.get(ATTR_ICON) == "mdi:play"
    assert group_state.attributes.get(ATTR_FRIENDLY_NAME) == "friendly_name"


async def test_setup(menuai: menuai) -> None:
    """Test setup method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)

    group_conf = OrderedDict()
    group_conf["test_group"] = "hello.world,sensor.happy"
    group_conf["empty_group"] = {"name": "Empty Group", "entities": None}
    assert await async_setup_component(menuai, "light", {})
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "group", {"group": group_conf})
    await menuai.async_block_till_done()

    test_group = await group.Group.async_create_group(
        menuai,
        "init_group",
        created_by_service=True,
        entity_ids=["light.Bowl", "light.Ceiling"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )
    await group.Group.async_create_group(
        menuai,
        "created_group",
        created_by_service=False,
        entity_ids=["light.Bowl", f"{test_group.entity_id}"],
        icon="mdi:work",
        mode=None,
        object_id=None,
        order=None,
    )
    await menuai.async_block_till_done()

    group_state = menuai.states.get(f"{group.DOMAIN}.created_group")
    assert group_state.state == STATE_ON
    assert {test_group.entity_id, "light.bowl"} == set(
        group_state.attributes["entity_id"]
    )
    assert group_state.attributes.get(group.ATTR_AUTO) is None
    assert group_state.attributes.get(ATTR_ICON) == "mdi:work"
    assert group_state.attributes.get(group.ATTR_ORDER) == 3

    group_state = menuai.states.get(f"{group.DOMAIN}.test_group")
    assert group_state.state == STATE_UNKNOWN
    assert set(group_state.attributes["entity_id"]) == {"sensor.happy", "hello.world"}
    assert group_state.attributes.get(group.ATTR_AUTO) is None
    assert group_state.attributes.get(ATTR_ICON) is None
    assert group_state.attributes.get(group.ATTR_ORDER) == 0


async def test_service_group_services(menuai: menuai) -> None:
    """Check if service are available."""
    with assert_setup_component(0, "group"):
        await async_setup_component(menuai, "group", {"group": {}})

    assert menuai.services.has_service("group", group.SERVICE_SET)
    assert menuai.services.has_service("group", group.SERVICE_REMOVE)


async def test_service_group_services_add_remove_entities(menuai: menuai) -> None:
    """Check if we can add and remove entities from group."""

    menuai.states.async_set("person.one", "Work")
    menuai.states.async_set("person.two", "Work")
    menuai.states.async_set("person.three", "home")

    assert await async_setup_component(menuai, "person", {})
    with assert_setup_component(0, "group"):
        await async_setup_component(menuai, "group", {"group": {}})
    await menuai.async_block_till_done()

    assert menuai.services.has_service("group", group.SERVICE_SET)

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_SET,
        {
            "object_id": "new_group",
            "name": "New Group",
            "entities": ["person.one", "person.two"],
        },
    )
    await menuai.async_block_till_done()

    group_state = menuai.states.get("group.new_group")
    assert group_state.state == "not_home"
    assert group_state.attributes["friendly_name"] == "New Group"
    assert list(group_state.attributes["entity_id"]) == ["person.one", "person.two"]

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_SET,
        {
            "object_id": "new_group",
            "add_entities": "person.three",
        },
    )
    await menuai.async_block_till_done()
    group_state = menuai.states.get("group.new_group")
    assert group_state.state == "home"
    assert "person.three" in list(group_state.attributes["entity_id"])

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_SET,
        {
            "object_id": "new_group",
            "remove_entities": "person.one",
        },
    )
    await menuai.async_block_till_done()
    group_state = menuai.states.get("group.new_group")
    assert group_state.state == "home"
    assert "person.one" not in list(group_state.attributes["entity_id"])


async def test_service_group_set_group_remove_group(menuai: menuai) -> None:
    """Check if service are available."""
    with assert_setup_component(0, "group"):
        await async_setup_component(menuai, "group", {"group": {}})

    common.async_set_group(menuai, "user_test_group", name="Test")
    await menuai.async_block_till_done()

    group_state = menuai.states.get("group.user_test_group")
    assert group_state
    assert group_state.attributes[group.ATTR_AUTO]
    assert group_state.attributes["friendly_name"] == "Test"

    common.async_set_group(menuai, "user_test_group", entity_ids=["test.entity_bla1"])
    await menuai.async_block_till_done()

    group_state = menuai.states.get("group.user_test_group")
    assert group_state
    assert group_state.attributes[group.ATTR_AUTO]
    assert group_state.attributes["friendly_name"] == "Test"
    assert list(group_state.attributes["entity_id"]) == ["test.entity_bla1"]

    common.async_set_group(
        menuai,
        "user_test_group",
        icon="mdi:camera",
        name="Test2",
        add=["test.entity_id2"],
    )
    await menuai.async_block_till_done()

    group_state = menuai.states.get("group.user_test_group")
    assert group_state
    assert group_state.attributes[group.ATTR_AUTO]
    assert group_state.attributes["friendly_name"] == "Test2"
    assert group_state.attributes["icon"] == "mdi:camera"
    assert sorted(group_state.attributes["entity_id"]) == sorted(
        ["test.entity_bla1", "test.entity_id2"]
    )

    common.async_remove(menuai, "user_test_group")
    await menuai.async_block_till_done()

    group_state = menuai.states.get("group.user_test_group")
    assert group_state is None


async def test_group_order(menuai: menuai) -> None:
    """Test that order gets incremented when creating a new group."""
    menuai.states.async_set("light.bowl", STATE_ON)

    assert await async_setup_component(menuai, "light", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_one": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_two": {"entities": "light.Bowl", "icon": "mdi:work"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").attributes["order"] == 0
    assert menuai.states.get("group.group_one").attributes["order"] == 1
    assert menuai.states.get("group.group_two").attributes["order"] == 2


async def test_group_order_with_dynamic_creation(menuai: menuai) -> None:
    """Test that order gets incremented when creating a new group."""
    menuai.states.async_set("light.bowl", STATE_ON)

    assert await async_setup_component(menuai, "light", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_one": {"entities": "light.Bowl", "icon": "mdi:work"},
                "group_two": {"entities": "light.Bowl", "icon": "mdi:work"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").attributes["order"] == 0
    assert menuai.states.get("group.group_one").attributes["order"] == 1
    assert menuai.states.get("group.group_two").attributes["order"] == 2

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_SET,
        {"object_id": "new_group", "name": "New Group", "entities": "light.bowl"},
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.new_group").attributes["order"] == 3

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_REMOVE,
        {
            "object_id": "new_group",
        },
    )
    await menuai.async_block_till_done()

    assert not menuai.states.get("group.new_group")

    await menuai.services.async_call(
        group.DOMAIN,
        group.SERVICE_SET,
        {"object_id": "new_group2", "name": "New Group 2", "entities": "light.bowl"},
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.new_group2").attributes["order"] == 4


async def test_group_persons(menuai: menuai) -> None:
    """Test group of persons."""
    menuai.states.async_set("person.one", "Work")
    menuai.states.async_set("person.two", "Work")
    menuai.states.async_set("person.three", "home")

    assert await async_setup_component(menuai, "person", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "person.one, person.two, person.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "home"


async def test_group_persons_and_device_trackers(menuai: menuai) -> None:
    """Test group of persons and device_tracker."""
    menuai.states.async_set("person.one", "Work")
    menuai.states.async_set("person.two", "Work")
    menuai.states.async_set("person.three", "Work")
    menuai.states.async_set("device_tracker.one", "home")

    assert await async_setup_component(menuai, "person", {})
    assert await async_setup_component(menuai, "device_tracker", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {
                    "entities": "device_tracker.one, person.one, person.two, person.three"
                },
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "home"


async def test_group_mixed_domains_on(menuai: menuai) -> None:
    """Test group of mixed domains that is on."""
    menuai.states.async_set("lock.alexander_garage_exit_door", "unlocked")
    menuai.states.async_set("binary_sensor.alexander_garage_side_door_open", "on")
    menuai.states.async_set("cover.small_garage_door", "open")

    for domain in ("lock", "binary_sensor", "cover"):
        assert await async_setup_component(menuai, domain, {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {
                    "all": "true",
                    "entities": "lock.alexander_garage_exit_door, binary_sensor.alexander_garage_side_door_open, cover.small_garage_door",
                },
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "on"


async def test_group_mixed_domains_off(menuai: menuai) -> None:
    """Test group of mixed domains that is off."""
    menuai.states.async_set("lock.alexander_garage_exit_door", "locked")
    menuai.states.async_set("binary_sensor.alexander_garage_side_door_open", "off")
    menuai.states.async_set("cover.small_garage_door", "closed")

    for domain in ("lock", "binary_sensor", "cover"):
        assert await async_setup_component(menuai, domain, {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {
                    "all": "true",
                    "entities": "lock.alexander_garage_exit_door, binary_sensor.alexander_garage_side_door_open, cover.small_garage_door",
                },
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "off"


@pytest.mark.parametrize(
    ("states", "group_state"),
    [
        (("locked", "locked", "unlocked"), "unlocked"),
        (("locked", "locked", "locked"), "locked"),
        (("locked", "locked", "open"), "unlocked"),
        (("locked", "unlocked", "open"), "unlocked"),
    ],
)
async def test_group_locks(menuai: menuai, states, group_state) -> None:
    """Test group of locks."""
    menuai.states.async_set("lock.one", states[0])
    menuai.states.async_set("lock.two", states[1])
    menuai.states.async_set("lock.three", states[2])

    assert await async_setup_component(menuai, "lock", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "lock.one, lock.two, lock.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == group_state


async def test_group_sensors(menuai: menuai) -> None:
    """Test group of sensors."""
    menuai.states.async_set("sensor.one", "locked")
    menuai.states.async_set("sensor.two", "on")
    menuai.states.async_set("sensor.three", "closed")

    assert await async_setup_component(menuai, "sensor", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "sensor.one, sensor.two, sensor.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "unknown"


async def test_group_climate_mixed(menuai: menuai) -> None:
    """Test group of climate with mixed states."""
    menuai.states.async_set("climate.one", "off")
    menuai.states.async_set("climate.two", "cool")
    menuai.states.async_set("climate.three", "heat")

    assert await async_setup_component(menuai, "climate", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "climate.one, climate.two, climate.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == STATE_ON


async def test_group_climate_all_cool(menuai: menuai) -> None:
    """Test group of climate all set to cool."""
    menuai.states.async_set("climate.one", "cool")
    menuai.states.async_set("climate.two", "cool")
    menuai.states.async_set("climate.three", "cool")

    assert await async_setup_component(menuai, "climate", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "climate.one, climate.two, climate.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == STATE_ON


async def test_group_climate_all_off(menuai: menuai) -> None:
    """Test group of climate all set to off."""
    menuai.states.async_set("climate.one", "off")
    menuai.states.async_set("climate.two", "off")
    menuai.states.async_set("climate.three", "off")

    assert await async_setup_component(menuai, "climate", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "climate.one, climate.two, climate.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == STATE_OFF


async def test_group_alarm(menuai: menuai) -> None:
    """Test group of alarm control panels."""
    menuai.states.async_set("alarm_control_panel.one", "armed_away")
    menuai.states.async_set("alarm_control_panel.two", "armed_home")
    menuai.states.async_set("alarm_control_panel.three", "armed_away")
    menuai.set_state(CoreState.stopped)

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {
                    "entities": "alarm_control_panel.one, alarm_control_panel.two, alarm_control_panel.three"
                },
            }
        },
    )
    assert await async_setup_component(menuai, "alarm_control_panel", {})
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert menuai.states.get("group.group_zero").state == STATE_ON


async def test_group_alarm_disarmed(menuai: menuai) -> None:
    """Test group of alarm control panels disarmed."""
    menuai.states.async_set("alarm_control_panel.one", "disarmed")
    menuai.states.async_set("alarm_control_panel.two", "disarmed")
    menuai.states.async_set("alarm_control_panel.three", "disarmed")

    assert await async_setup_component(menuai, "alarm_control_panel", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {
                    "entities": "alarm_control_panel.one, alarm_control_panel.two, alarm_control_panel.three"
                },
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == STATE_OFF


async def test_group_vacuum_off(menuai: menuai) -> None:
    """Test group of vacuums."""
    menuai.states.async_set("vacuum.one", "docked")
    menuai.states.async_set("vacuum.two", "off")
    menuai.states.async_set("vacuum.three", "off")
    menuai.set_state(CoreState.stopped)

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "vacuum.one, vacuum.two, vacuum.three"},
            }
        },
    )
    assert await async_setup_component(menuai, "vacuum", {})
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert menuai.states.get("group.group_zero").state == STATE_OFF


async def test_group_vacuum_on(menuai: menuai) -> None:
    """Test group of vacuums."""
    menuai.states.async_set("vacuum.one", "cleaning")
    menuai.states.async_set("vacuum.two", "off")
    menuai.states.async_set("vacuum.three", "off")

    assert await async_setup_component(menuai, "vacuum", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "vacuum.one, vacuum.two, vacuum.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == STATE_ON


@pytest.mark.parametrize(
    ("entity_state_list", "group_state"),
    [
        (
            {
                "device_tracker.one": "not_home",
                "device_tracker.two": "not_home",
                "device_tracker.three": "not_home",
            },
            "not_home",
        ),
        (
            {
                "device_tracker.one": "home",
                "device_tracker.two": "not_home",
                "device_tracker.three": "not_home",
            },
            "home",
        ),
        (
            {
                "device_tracker.one": "home",
                "device_tracker.two": "elsewhere",
                "device_tracker.three": "not_home",
            },
            "home",
        ),
        (
            {
                "device_tracker.one": "not_home",
                "device_tracker.two": "elsewhere",
                "device_tracker.three": "not_home",
            },
            "not_home",
        ),
    ],
)
async def test_device_tracker_or_person_not_home(
    menuai: menuai,
    entity_state_list: dict[str, str],
    group_state: str,
) -> None:
    """Test group of device_tracker not_home."""
    await async_setup_component(menuai, "device_tracker", {})
    await async_setup_component(menuai, "person", {})
    await menuai.async_block_till_done()
    for entity_id, state in entity_state_list.items():
        menuai.states.async_set(entity_id, state)

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": ", ".join(entity_state_list)},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == group_state


async def test_light_removed(menuai: menuai) -> None:
    """Test group of lights when one is removed."""
    menuai.states.async_set("light.one", "off")
    menuai.states.async_set("light.two", "off")
    menuai.states.async_set("light.three", "on")

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "light.one, light.two, light.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "on"

    menuai.states.async_remove("light.three")
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "off"


async def test_switch_removed(menuai: menuai) -> None:
    """Test group of switches when one is removed."""
    menuai.states.async_set("switch.one", "off")
    menuai.states.async_set("switch.two", "off")
    menuai.states.async_set("switch.three", "on")

    menuai.set_state(CoreState.stopped)
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "group_zero": {"entities": "switch.one, switch.two, switch.three"},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "unknown"
    assert await async_setup_component(menuai, "switch", {})
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert menuai.states.get("group.group_zero").state == "on"

    menuai.states.async_remove("switch.three")
    await menuai.async_block_till_done()

    assert menuai.states.get("group.group_zero").state == "off"


async def test_lights_added_after_group(menuai: menuai) -> None:
    """Test lights added after group."""

    entity_ids = [
        "light.living_front_ri",
        "light.living_back_lef",
        "light.living_back_cen",
        "light.living_front_le",
        "light.living_front_ce",
        "light.living_back_rig",
    ]

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "living_room_downlights": {"entities": entity_ids},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downlights").state == "unknown"

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "off")
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downlights").state == "off"


async def test_lights_added_before_group(menuai: menuai) -> None:
    """Test lights added before group."""

    entity_ids = [
        "light.living_front_ri",
        "light.living_back_lef",
        "light.living_back_cen",
        "light.living_front_le",
        "light.living_front_ce",
        "light.living_back_rig",
    ]

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "off")
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "living_room_downlights": {"entities": entity_ids},
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downlights").state == "off"


async def test_cover_added_after_group(menuai: menuai) -> None:
    """Test cover added after group."""

    entity_ids = [
        "cover.upstairs",
        "cover.downstairs",
    ]

    assert await async_setup_component(menuai, "cover", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "shades": {"entities": entity_ids},
            }
        },
    )
    await menuai.async_block_till_done()

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "open")
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert menuai.states.get("group.shades").state == "open"

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "closed")

    await menuai.async_block_till_done()
    assert menuai.states.get("group.shades").state == "closed"


async def test_group_that_references_a_group_of_lights(menuai: menuai) -> None:
    """Group that references a group of lights."""

    entity_ids = [
        "light.living_front_ri",
        "light.living_back_lef",
    ]
    menuai.set_state(CoreState.stopped)

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "off")
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "living_room_downlights": {"entities": entity_ids},
                "grouped_group": {
                    "entities": ["group.living_room_downlights", *entity_ids]
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downlights").state == "off"
    assert menuai.states.get("group.grouped_group").state == "off"


async def test_group_that_references_a_group_of_covers(menuai: menuai) -> None:
    """Group that references a group of covers."""

    entity_ids = [
        "cover.living_front_ri",
        "cover.living_back_lef",
    ]
    menuai.set_state(CoreState.stopped)

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "closed")
    await menuai.async_block_till_done()
    assert await async_setup_component(menuai, "cover", {})

    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "living_room_downcover": {"entities": entity_ids},
                "grouped_group": {
                    "entities": ["group.living_room_downlights", *entity_ids]
                },
            }
        },
    )

    assert await async_setup_component(menuai, "cover", {})
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downcover").state == "closed"
    assert menuai.states.get("group.grouped_group").state == "closed"


async def test_group_that_references_two_groups_of_covers(menuai: menuai) -> None:
    """Group that references a group of covers."""

    entity_ids = [
        "cover.living_front_ri",
        "cover.living_back_lef",
    ]
    menuai.set_state(CoreState.stopped)

    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "closed")
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "cover", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "living_room_downcover": {"entities": entity_ids},
                "living_room_upcover": {"entities": entity_ids},
                "grouped_group": {
                    "entities": [
                        "group.living_room_downlights",
                        "group.living_room_upcover",
                    ]
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    assert menuai.states.get("group.living_room_downcover").state == "closed"
    assert menuai.states.get("group.living_room_upcover").state == "closed"
    assert menuai.states.get("group.grouped_group").state == "closed"


async def test_group_that_references_two_types_of_groups(menuai: menuai) -> None:
    """Group that references a group of covers and device_trackers."""

    group_1_entity_ids = [
        "cover.living_front_ri",
        "cover.living_back_lef",
    ]
    group_2_entity_ids = [
        "device_tracker.living_front_ri",
        "device_tracker.living_back_lef",
    ]
    menuai.set_state(CoreState.stopped)

    for entity_id in group_1_entity_ids:
        menuai.states.async_set(entity_id, "closed")
    for entity_id in group_2_entity_ids:
        menuai.states.async_set(entity_id, "home")
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "cover", {})
    assert await async_setup_component(menuai, "device_tracker", {})
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "covers": {"entities": group_1_entity_ids},
                "device_trackers": {"entities": group_2_entity_ids},
                "grouped_group": {
                    "entities": ["group.covers", "group.device_trackers"]
                },
            }
        },
    )
    assert await async_setup_component(menuai, "cover", {})
    await menuai.async_block_till_done()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    assert menuai.states.get("group.covers").state == "closed"
    assert menuai.states.get("group.device_trackers").state == "home"
    assert menuai.states.get("group.grouped_group").state == "on"


async def test_plant_group(menuai: menuai) -> None:
    """Test plant states can be grouped."""

    entity_ids = [
        "plant.upstairs",
        "plant.downstairs",
    ]

    assert await async_setup_component(
        menuai,
        "plant",
        {
            "plant": {
                "plantname": {
                    "sensors": {
                        "moisture": "sensor.mqtt_plant_moisture",
                        "battery": "sensor.mqtt_plant_battery",
                        "temperature": "sensor.mqtt_plant_temperature",
                        "conductivity": "sensor.mqtt_plant_conductivity",
                        "brightness": "sensor.mqtt_plant_brightness",
                    },
                    "min_moisture": 20,
                    "max_moisture": 60,
                    "min_battery": 17,
                    "min_conductivity": 500,
                    "min_temperature": 15,
                    "min_brightness": 500,
                }
            }
        },
    )
    assert await async_setup_component(
        menuai,
        "group",
        {
            "group": {
                "plants": {"entities": entity_ids},
                "plant_with_binary_sensors": {
                    "entities": [*entity_ids, "binary_sensor.planter"]
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("binary_sensor.planter", "off")
    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "ok")
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert menuai.states.get("group.plants").state == "ok"
    assert menuai.states.get("group.plant_with_binary_sensors").state == "off"

    menuai.states.async_set("binary_sensor.planter", "on")
    for entity_id in entity_ids:
        menuai.states.async_set(entity_id, "problem")

    await menuai.async_block_till_done()
    assert menuai.states.get("group.plants").state == "problem"
    assert menuai.states.get("group.plant_with_binary_sensors").state == "on"


@pytest.mark.parametrize(
    ("group_type", "member_state", "extra_options"),
    [
        ("binary_sensor", "on", {"all": False}),
        ("cover", "open", {}),
        ("fan", "on", {}),
        ("light", "on", {"all": False}),
        ("media_player", "on", {}),
        (
            "sensor",
            "1",
            {
                "all": True,
                "type": "max",
                "round_digits": 2.0,
                "state_class": "measurement",
            },
        ),
    ],
)
async def test_setup_and_remove_config_entry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    group_type: str,
    member_state: str,
    extra_options: dict[str, Any],
) -> None:
    """Test removing a config entry."""
    members1 = [f"{group_type}.one", f"{group_type}.two"]

    for member in members1:
        menuai.states.async_set(member, member_state, {})

    # Setup the config entry
    group_config_entry = MockConfigEntry(
        data={},
        domain=group.DOMAIN,
        options={
            "entities": members1,
            "group_type": group_type,
            "name": "Bed Room",
            **extra_options,
        },
        title="Bed Room",
    )
    group_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(group_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the state and entity registry entry are present
    state = menuai.states.get(f"{group_type}.bed_room")
    assert state.attributes["entity_id"] == members1
    assert entity_registry.async_get(f"{group_type}.bed_room") is not None

    # Remove the config entry
    assert await menuai.config_entries.async_remove(group_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert menuai.states.get(f"{group_type}.bed_room") is None
    assert entity_registry.async_get(f"{group_type}.bed_room") is None


@pytest.mark.parametrize(
    ("hide_members", "hidden_by_initial", "hidden_by"),
    [
        (False, er.RegistryEntryHider.INTEGRATION, er.RegistryEntryHider.INTEGRATION),
        (False, None, None),
        (False, er.RegistryEntryHider.USER, er.RegistryEntryHider.USER),
        (True, er.RegistryEntryHider.INTEGRATION, None),
        (True, None, None),
        (True, er.RegistryEntryHider.USER, er.RegistryEntryHider.USER),
    ],
)
@pytest.mark.parametrize(
    ("group_type", "extra_options"),
    [
        ("binary_sensor", {"all": False}),
        ("cover", {}),
        ("fan", {}),
        ("light", {"all": False}),
        ("media_player", {}),
    ],
)
async def test_unhide_members_on_remove(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    group_type: str,
    extra_options: dict[str, Any],
    hide_members: bool,
    hidden_by_initial: er.RegistryEntryHider,
    hidden_by: str,
) -> None:
    """Test removing a config entry."""
    entry1 = entity_registry.async_get_or_create(
        group_type,
        "test",
        "unique1",
        suggested_object_id="one",
        hidden_by=hidden_by_initial,
    )
    assert entry1.entity_id == f"{group_type}.one"

    entry3 = entity_registry.async_get_or_create(
        group_type,
        "test",
        "unique3",
        suggested_object_id="three",
        hidden_by=hidden_by_initial,
    )
    assert entry3.entity_id == f"{group_type}.three"

    entry4 = entity_registry.async_get_or_create(
        group_type,
        "test",
        "unique4",
        suggested_object_id="four",
    )
    assert entry4.entity_id == f"{group_type}.four"

    members = [f"{group_type}.one", f"{group_type}.two", entry3.id, entry4.id]

    # Setup the config entry
    group_config_entry = MockConfigEntry(
        data={},
        domain=group.DOMAIN,
        options={
            "entities": members,
            "group_type": group_type,
            "hide_members": hide_members,
            "name": "Bed Room",
            **extra_options,
        },
        title="Bed Room",
    )
    group_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(group_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the state is present
    assert menuai.states.get(f"{group_type}.bed_room")

    # Remove one entity registry entry, to make sure this does not trip up config entry
    # removal
    entity_registry.async_remove(entry4.entity_id)

    # Remove the config entry
    assert await menuai.config_entries.async_remove(group_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the group members are unhidden
    assert entity_registry.async_get(f"{group_type}.one").hidden_by == hidden_by
    assert entity_registry.async_get(f"{group_type}.three").hidden_by == hidden_by


@pytest.mark.parametrize("grouped_groups", [False, True])
@pytest.mark.parametrize(
    ("on_off_states1", "on_off_states2"),
    [
        (
            (
                {
                    "on_beer",
                    "on_milk",
                },
                "on_beer",  # default ON state test1
                "off_water",  # default OFF state test1
            ),
            (
                {
                    "on_beer",
                    "on_milk",
                },
                "on_milk",  # default ON state test2
                "off_wine",  # default OFF state test2
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    ("entity_and_state1_state_2", "group_state1", "group_state2"),
    [
        # All OFF states, no change, so group stays OFF
        (
            [
                ("test1.ent1", "off_water", "off_water"),
                ("test1.ent2", "off_water", "off_water"),
                ("test2.ent1", "off_wine", "off_wine"),
                ("test2.ent2", "off_wine", "off_wine"),
            ],
            STATE_OFF,
            STATE_OFF,
        ),
        # All entities have state on_milk, but the state groups
        # are different so the group status defaults to ON / OFF
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_milk"),
                ("test2.ent1", "off_wine", "on_milk"),
                ("test2.ent2", "off_wine", "on_milk"),
            ],
            STATE_OFF,
            STATE_ON,
        ),
        # Only test1 entities in group, all at ON state
        # group returns the default ON state `on_beer`
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_beer"),
            ],
            "off_water",
            "on_beer",
        ),
        # Only test1 entities in group, all at ON state
        # group returns the default ON state `on_beer`
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_milk"),
            ],
            "off_water",
            "on_beer",
        ),
        # Only test2 entities in group, all at ON state
        # group returns the default ON state `on_milk`
        (
            [
                ("test2.ent1", "off_wine", "on_milk"),
                ("test2.ent2", "off_wine", "on_milk"),
            ],
            "off_wine",
            "on_milk",
        ),
    ],
)
async def test_entity_platforms_with_multiple_on_states_no_state_match(
    menuai: menuai,
    on_off_states1: tuple[set[str], str, str],
    on_off_states2: tuple[set[str], str, str],
    entity_and_state1_state_2: tuple[str, str | None, str | None],
    group_state1: str,
    group_state2: str,
    grouped_groups: bool,
) -> None:
    """Test custom entity platforms with multiple ON states without state match.

    The test group 1 an 2 non matching (default_state_on, state_off) pairs.
    """
    await help_test_mixed_entity_platforms_on_off_state_test(
        menuai,
        on_off_states1,
        on_off_states2,
        entity_and_state1_state_2,
        group_state1,
        group_state2,
        grouped_groups,
    )


@pytest.mark.parametrize("grouped_groups", [False, True])
@pytest.mark.parametrize(
    ("on_off_states1", "on_off_states2"),
    [
        (
            (
                {
                    "on_beer",
                    "on_milk",
                },
                "on_beer",  # default ON state test1
                "off_water",  # default OFF state test1
            ),
            (
                {
                    "on_beer",
                    "on_wine",
                },
                "on_beer",  # default ON state test2
                "off_water",  # default OFF state test2
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    ("entity_and_state1_state_2", "group_state1", "group_state2"),
    [
        # All OFF states, no change, so group stays OFF
        (
            [
                ("test1.ent1", "off_water", "off_water"),
                ("test1.ent2", "off_water", "off_water"),
                ("test2.ent1", "off_water", "off_water"),
                ("test2.ent2", "off_water", "off_water"),
            ],
            "off_water",
            "off_water",
        ),
        # All entities have ON state `on_milk`
        # but the group state will default to on_beer
        # which is the default ON state for both integrations.
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_milk"),
                ("test2.ent1", "off_water", "on_milk"),
                ("test2.ent2", "off_water", "on_milk"),
            ],
            "off_water",
            "on_beer",
        ),
        # Only test1 entities in group, all at ON state
        # group returns the default ON state `on_beer`
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_beer"),
            ],
            "off_water",
            "on_beer",
        ),
        # Only test1 entities in group, all at ON state
        # group returns the default ON state `on_beer`
        (
            [
                ("test1.ent1", "off_water", "on_milk"),
                ("test1.ent2", "off_water", "on_milk"),
            ],
            "off_water",
            "on_beer",
        ),
        # Only test2 entities in group, all at ON state
        # group returns the default ON state `on_milk`
        (
            [
                ("test2.ent1", "off_water", "on_wine"),
                ("test2.ent2", "off_water", "on_wine"),
            ],
            "off_water",
            "on_beer",
        ),
    ],
)
async def test_entity_platforms_with_multiple_on_states_with_state_match(
    menuai: menuai,
    on_off_states1: tuple[set[str], str, str],
    on_off_states2: tuple[set[str], str, str],
    entity_and_state1_state_2: tuple[str, str | None, str | None],
    group_state1: str,
    group_state2: str,
    grouped_groups: bool,
) -> None:
    """Test custom entity platforms with multiple ON states with a state match.

    The integrations test1 and test2 have matching (default_state_on, state_off) pairs.
    """
    await help_test_mixed_entity_platforms_on_off_state_test(
        menuai,
        on_off_states1,
        on_off_states2,
        entity_and_state1_state_2,
        group_state1,
        group_state2,
        grouped_groups,
    )
