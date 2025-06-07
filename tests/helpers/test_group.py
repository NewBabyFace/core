"""Test the group helper."""

from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import group


async def test_expand_entity_ids(menuai: menuai) -> None:
    """Test expand_entity_ids method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)
    menuai.states.async_set(
        "group.init_group", STATE_ON, {ATTR_ENTITY_ID: ["light.bowl", "light.ceiling"]}
    )
    state = menuai.states.get("group.init_group")
    assert state is not None
    assert state.attributes[ATTR_ENTITY_ID] == ["light.bowl", "light.ceiling"]

    assert sorted(group.expand_entity_ids(menuai, ["group.init_group"])) == [
        "light.bowl",
        "light.ceiling",
    ]
    assert sorted(group.expand_entity_ids(menuai, ["group.INIT_group"])) == [
        "light.bowl",
        "light.ceiling",
    ]


async def test_expand_entity_ids_does_not_return_duplicates(
    menuai: menuai,
) -> None:
    """Test that expand_entity_ids does not return duplicates."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)
    menuai.states.async_set(
        "group.init_group", STATE_ON, {ATTR_ENTITY_ID: ["light.bowl", "light.ceiling"]}
    )

    assert sorted(
        group.expand_entity_ids(menuai, ["group.init_group", "light.Ceiling"])
    ) == ["light.bowl", "light.ceiling"]

    assert sorted(
        group.expand_entity_ids(menuai, ["light.bowl", "group.init_group"])
    ) == ["light.bowl", "light.ceiling"]


async def test_expand_entity_ids_recursive(menuai: menuai) -> None:
    """Test expand_entity_ids method with a group that contains itself."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)
    menuai.states.async_set(
        "group.init_group", STATE_ON, {ATTR_ENTITY_ID: ["light.bowl", "light.ceiling"]}
    )

    menuai.states.async_set(
        "group.rec_group",
        STATE_ON,
        {ATTR_ENTITY_ID: ["group.init_group", "light.ceiling"]},
    )

    assert sorted(group.expand_entity_ids(menuai, ["group.rec_group"])) == [
        "light.bowl",
        "light.ceiling",
    ]


async def test_expand_entity_ids_ignores_non_strings(menuai: menuai) -> None:
    """Test that non string elements in lists are ignored."""
    assert group.expand_entity_ids(menuai, [5, True]) == []


async def test_get_entity_ids(menuai: menuai) -> None:
    """Test get_entity_ids method."""
    menuai.states.async_set("light.Bowl", STATE_ON)
    menuai.states.async_set("light.Ceiling", STATE_OFF)
    menuai.states.async_set(
        "group.init_group", STATE_ON, {ATTR_ENTITY_ID: ["light.bowl", "light.ceiling"]}
    )

    assert sorted(group.get_entity_ids(menuai, "group.init_group")) == [
        "light.bowl",
        "light.ceiling",
    ]


async def test_get_entity_ids_with_domain_filter(menuai: menuai) -> None:
    """Test if get_entity_ids works with a domain_filter."""
    menuai.states.async_set("switch.AC", STATE_OFF)
    menuai.states.async_set(
        "group.mixed_group", STATE_ON, {ATTR_ENTITY_ID: ["light.bowl", "switch.ac"]}
    )

    assert group.get_entity_ids(menuai, "group.mixed_group", domain_filter="switch") == [
        "switch.ac"
    ]


async def test_get_entity_ids_with_non_existing_group_name(menuai: menuai) -> None:
    """Test get_entity_ids with a non existing group."""
    assert group.get_entity_ids(menuai, "non_existing") == []


async def test_get_entity_ids_with_non_group_state(menuai: menuai) -> None:
    """Test get_entity_ids with a non group state."""
    assert group.get_entity_ids(menuai, "switch.AC") == []
