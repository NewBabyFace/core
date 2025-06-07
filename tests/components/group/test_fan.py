"""The tests for the group fan platform."""

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from menuai import config as menuai_config
from menuai.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_OSCILLATE,
    SERVICE_SET_DIRECTION,
    SERVICE_SET_PERCENTAGE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    FanEntityFeature,
)
from menuai.components.group import SERVICE_RELOAD
from menuai.components.group.fan import DEFAULT_NAME
from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITIES,
    CONF_UNIQUE_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import CoreState, menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import assert_setup_component, get_fixture_path

FAN_GROUP = "fan.fan_group"

MISSING_FAN_ENTITY_ID = "fan.missing"
LIVING_ROOM_FAN_ENTITY_ID = "fan.living_room_fan"
PERCENTAGE_FULL_FAN_ENTITY_ID = "fan.percentage_full_fan"
CEILING_FAN_ENTITY_ID = "fan.ceiling_fan"
PERCENTAGE_LIMITED_FAN_ENTITY_ID = "fan.percentage_limited_fan"

FULL_FAN_ENTITY_IDS = [LIVING_ROOM_FAN_ENTITY_ID, PERCENTAGE_FULL_FAN_ENTITY_ID]
LIMITED_FAN_ENTITY_IDS = [CEILING_FAN_ENTITY_ID, PERCENTAGE_LIMITED_FAN_ENTITY_ID]


FULL_SUPPORT_FEATURES = (
    FanEntityFeature.SET_SPEED | FanEntityFeature.DIRECTION | FanEntityFeature.OSCILLATE
)


CONFIG_MISSING_FAN = {
    FAN_DOMAIN: [
        {"platform": "demo"},
        {
            "platform": "group",
            CONF_ENTITIES: [
                MISSING_FAN_ENTITY_ID,
                *FULL_FAN_ENTITY_IDS,
                *LIMITED_FAN_ENTITY_IDS,
            ],
        },
    ]
}

CONFIG_FULL_SUPPORT = {
    FAN_DOMAIN: [
        {"platform": "demo"},
        {
            "platform": "group",
            CONF_ENTITIES: [*FULL_FAN_ENTITY_IDS],
        },
    ]
}

CONFIG_LIMITED_SUPPORT = {
    FAN_DOMAIN: [
        {
            "platform": "group",
            CONF_ENTITIES: [*LIMITED_FAN_ENTITY_IDS],
        },
    ]
}


CONFIG_ATTRIBUTES = {
    FAN_DOMAIN: {
        "platform": "group",
        CONF_ENTITIES: [*FULL_FAN_ENTITY_IDS, *LIMITED_FAN_ENTITY_IDS],
        CONF_UNIQUE_ID: "unique_identifier",
    }
}


@pytest.fixture
async def setup_comp(
    menuai: menuai, config_count: tuple[dict[str, Any], int]
) -> None:
    """Set up group fan component."""
    config, count = config_count
    with assert_setup_component(count, FAN_DOMAIN):
        await async_setup_component(menuai, FAN_DOMAIN, config)
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()


@pytest.mark.parametrize("config_count", [(CONFIG_ATTRIBUTES, 1)])
@pytest.mark.usefixtures("setup_comp")
async def test_state(menuai: menuai, entity_registry: er.EntityRegistry) -> None:
    """Test handling of state.

    The group state is on if at least one group member is on.
    Otherwise, the group state is off.
    """
    state = menuai.states.get(FAN_GROUP)
    # No entity has a valid state -> group state unavailable
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert ATTR_ENTITY_ID not in state.attributes
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0

    # Test group members exposed as attribute
    menuai.states.async_set(CEILING_FAN_ENTITY_ID, STATE_UNKNOWN, {})
    await menuai.async_block_till_done()
    state = menuai.states.get(FAN_GROUP)
    assert state.attributes[ATTR_ENTITY_ID] == [
        *FULL_FAN_ENTITY_IDS,
        *LIMITED_FAN_ENTITY_IDS,
    ]

    # All group members unavailable -> unavailable
    menuai.states.async_set(CEILING_FAN_ENTITY_ID, STATE_UNAVAILABLE)
    menuai.states.async_set(LIVING_ROOM_FAN_ENTITY_ID, STATE_UNAVAILABLE)
    menuai.states.async_set(PERCENTAGE_FULL_FAN_ENTITY_ID, STATE_UNAVAILABLE)
    menuai.states.async_set(PERCENTAGE_LIMITED_FAN_ENTITY_ID, STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_UNAVAILABLE

    # The group state is unknown if all group members are unknown or unavailable.
    for state_1 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        for state_2 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            for state_3 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                menuai.states.async_set(CEILING_FAN_ENTITY_ID, state_1, {})
                menuai.states.async_set(LIVING_ROOM_FAN_ENTITY_ID, state_2, {})
                menuai.states.async_set(PERCENTAGE_FULL_FAN_ENTITY_ID, state_3, {})
                menuai.states.async_set(
                    PERCENTAGE_LIMITED_FAN_ENTITY_ID, STATE_UNKNOWN, {}
                )
                await menuai.async_block_till_done()
                state = menuai.states.get(FAN_GROUP)
                assert state.state == STATE_UNKNOWN

    # The group state is off if all group members are off, unknown or unavailable.
    for state_1 in (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN):
        for state_2 in (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN):
            for state_3 in (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN):
                menuai.states.async_set(CEILING_FAN_ENTITY_ID, state_1, {})
                menuai.states.async_set(LIVING_ROOM_FAN_ENTITY_ID, state_2, {})
                menuai.states.async_set(PERCENTAGE_FULL_FAN_ENTITY_ID, state_3, {})
                menuai.states.async_set(PERCENTAGE_LIMITED_FAN_ENTITY_ID, STATE_OFF, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(FAN_GROUP)
                assert state.state == STATE_OFF

    # At least one member on -> group on
    for state_1 in (STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN):
        for state_2 in (STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN):
            for state_3 in (STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN):
                menuai.states.async_set(CEILING_FAN_ENTITY_ID, state_1, {})
                menuai.states.async_set(LIVING_ROOM_FAN_ENTITY_ID, state_2, {})
                menuai.states.async_set(PERCENTAGE_FULL_FAN_ENTITY_ID, state_3, {})
                menuai.states.async_set(PERCENTAGE_LIMITED_FAN_ENTITY_ID, STATE_ON, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(FAN_GROUP)
                assert state.state == STATE_ON

    # now remove an entity
    menuai.states.async_remove(PERCENTAGE_LIMITED_FAN_ENTITY_ID)
    await menuai.async_block_till_done()
    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_UNKNOWN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0

    # now remove all entities
    menuai.states.async_remove(CEILING_FAN_ENTITY_ID)
    menuai.states.async_remove(LIVING_ROOM_FAN_ENTITY_ID)
    menuai.states.async_remove(PERCENTAGE_FULL_FAN_ENTITY_ID)
    await menuai.async_block_till_done()
    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_UNAVAILABLE
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0

    # Test entity registry integration
    entry = entity_registry.async_get(FAN_GROUP)
    assert entry
    assert entry.unique_id == "unique_identifier"


@pytest.mark.parametrize("config_count", [(CONFIG_ATTRIBUTES, 1)])
@pytest.mark.usefixtures("setup_comp")
async def test_attributes(menuai: menuai) -> None:
    """Test handling of state attributes."""
    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert ATTR_ENTITY_ID not in state.attributes
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0
    menuai.states.async_set(CEILING_FAN_ENTITY_ID, STATE_ON, {})
    menuai.states.async_set(LIVING_ROOM_FAN_ENTITY_ID, STATE_ON, {})
    menuai.states.async_set(PERCENTAGE_FULL_FAN_ENTITY_ID, STATE_ON, {})
    menuai.states.async_set(PERCENTAGE_LIMITED_FAN_ENTITY_ID, STATE_ON, {})
    await menuai.async_block_till_done()
    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_ENTITY_ID] == [
        *FULL_FAN_ENTITY_IDS,
        *LIMITED_FAN_ENTITY_IDS,
    ]

    # Add Entity that supports speed
    menuai.states.async_set(
        CEILING_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.SET_SPEED,
            ATTR_PERCENTAGE: 50,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == FanEntityFeature.SET_SPEED
    assert ATTR_PERCENTAGE in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert ATTR_ASSUMED_STATE not in state.attributes

    # Add Entity with a different speed should not set assumed state
    menuai.states.async_set(
        PERCENTAGE_LIMITED_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.SET_SPEED,
            ATTR_PERCENTAGE: 75,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == int((50 + 75) / 2)


@pytest.mark.parametrize("config_count", [(CONFIG_FULL_SUPPORT, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_direction_oscillating(menuai: menuai) -> None:
    """Test handling of direction and oscillating attributes."""

    menuai.states.async_set(
        LIVING_ROOM_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: True,
            ATTR_DIRECTION: DIRECTION_FORWARD,
            ATTR_PERCENTAGE: 50,
        },
    )
    menuai.states.async_set(
        PERCENTAGE_FULL_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: True,
            ATTR_DIRECTION: DIRECTION_FORWARD,
            ATTR_PERCENTAGE: 50,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert state.attributes[ATTR_ENTITY_ID] == [*FULL_FAN_ENTITY_IDS]
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == FULL_SUPPORT_FEATURES
    assert ATTR_PERCENTAGE in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.attributes[ATTR_OSCILLATING] is True
    assert state.attributes[ATTR_DIRECTION] == DIRECTION_FORWARD
    assert ATTR_ASSUMED_STATE not in state.attributes

    # Add Entity with a different direction should not set assumed state
    menuai.states.async_set(
        PERCENTAGE_FULL_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: True,
            ATTR_DIRECTION: DIRECTION_REVERSE,
            ATTR_PERCENTAGE: 50,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert ATTR_PERCENTAGE in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.attributes[ATTR_OSCILLATING] is True

    # Now that everything is the same, no longer assumed state

    menuai.states.async_set(
        LIVING_ROOM_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: True,
            ATTR_DIRECTION: DIRECTION_REVERSE,
            ATTR_PERCENTAGE: 50,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert ATTR_PERCENTAGE in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.attributes[ATTR_OSCILLATING] is True
    assert state.attributes[ATTR_DIRECTION] == DIRECTION_REVERSE
    assert ATTR_ASSUMED_STATE not in state.attributes

    menuai.states.async_set(
        LIVING_ROOM_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: False,
            ATTR_DIRECTION: DIRECTION_FORWARD,
            ATTR_PERCENTAGE: 50,
        },
    )
    menuai.states.async_set(
        PERCENTAGE_FULL_FAN_ENTITY_ID,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: FULL_SUPPORT_FEATURES,
            ATTR_OSCILLATING: False,
            ATTR_DIRECTION: DIRECTION_FORWARD,
            ATTR_PERCENTAGE: 50,
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(FAN_GROUP)
    assert state.state == STATE_ON
    assert ATTR_PERCENTAGE in state.attributes
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.attributes[ATTR_OSCILLATING] is False
    assert state.attributes[ATTR_DIRECTION] == DIRECTION_FORWARD
    assert ATTR_ASSUMED_STATE not in state.attributes


@pytest.mark.parametrize("config_count", [(CONFIG_MISSING_FAN, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_state_missing_entity_id(menuai: menuai) -> None:
    """Test we can still setup with a missing entity id."""
    state = menuai.states.get(FAN_GROUP)
    await menuai.async_block_till_done()
    assert state.state == STATE_OFF


async def test_setup_before_started(menuai: menuai) -> None:
    """Test we can setup before starting."""
    menuai.set_state(CoreState.stopped)
    assert await async_setup_component(menuai, FAN_DOMAIN, CONFIG_MISSING_FAN)

    await menuai.async_block_till_done()
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get(FAN_GROUP).state == STATE_OFF


@pytest.mark.parametrize("config_count", [(CONFIG_MISSING_FAN, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_reload(menuai: menuai) -> None:
    """Test the ability to reload fans."""
    await menuai.async_block_till_done()
    await menuai.async_start()

    await menuai.async_block_till_done()
    assert menuai.states.get(FAN_GROUP).state == STATE_OFF

    yaml_path = get_fixture_path("fan_configuration.yaml", "group")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            "group",
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert menuai.states.get(FAN_GROUP) is None
    assert menuai.states.get("fan.upstairs_fans") is not None


@pytest.mark.parametrize("config_count", [(CONFIG_FULL_SUPPORT, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_service_calls(menuai: menuai) -> None:
    """Test calling services."""
    await menuai.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: FAN_GROUP}, blocking=True
    )
    assert menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID).state == STATE_ON
    assert menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID).state == STATE_ON
    assert menuai.states.get(FAN_GROUP).state == STATE_ON

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_PERCENTAGE: 66},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_PERCENTAGE] == 66
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_PERCENTAGE] == 66
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_PERCENTAGE] == 66
    assert fan_group_state.attributes[ATTR_PERCENTAGE_STEP] == 100 / 3

    await menuai.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: FAN_GROUP}, blocking=True
    )
    assert menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID).state == STATE_OFF
    assert menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID).state == STATE_OFF
    assert menuai.states.get(FAN_GROUP).state == STATE_OFF

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_PERCENTAGE] == 100
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_PERCENTAGE] == 100
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_PERCENTAGE] == 100

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_PERCENTAGE: 0},
        blocking=True,
    )
    assert menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID).state == STATE_OFF
    assert menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID).state == STATE_OFF
    assert menuai.states.get(FAN_GROUP).state == STATE_OFF

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_OSCILLATING: True},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_OSCILLATING] is True
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_OSCILLATING] is True
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_OSCILLATING] is True

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_OSCILLATING: False},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_OSCILLATING] is False
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_OSCILLATING] is False
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_OSCILLATING] is False

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_DIRECTION,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_DIRECTION: DIRECTION_FORWARD},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_DIRECTION] == DIRECTION_FORWARD
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_DIRECTION] == DIRECTION_FORWARD
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_DIRECTION] == DIRECTION_FORWARD

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_DIRECTION,
        {ATTR_ENTITY_ID: FAN_GROUP, ATTR_DIRECTION: DIRECTION_REVERSE},
        blocking=True,
    )
    living_room_fan_state = menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID)
    assert living_room_fan_state.attributes[ATTR_DIRECTION] == DIRECTION_REVERSE
    percentage_full_fan_state = menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID)
    assert percentage_full_fan_state.attributes[ATTR_DIRECTION] == DIRECTION_REVERSE
    fan_group_state = menuai.states.get(FAN_GROUP)
    assert fan_group_state.attributes[ATTR_DIRECTION] == DIRECTION_REVERSE


async def test_nested_group(menuai: menuai) -> None:
    """Test nested fan group."""
    await async_setup_component(
        menuai,
        FAN_DOMAIN,
        {
            FAN_DOMAIN: [
                {"platform": "demo"},
                {
                    "platform": "group",
                    "entities": ["fan.bedroom_group"],
                    "name": "Nested Group",
                },
                {
                    "platform": "group",
                    CONF_ENTITIES: [
                        LIVING_ROOM_FAN_ENTITY_ID,
                        PERCENTAGE_FULL_FAN_ENTITY_ID,
                    ],
                    "name": "Bedroom Group",
                },
            ]
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("fan.bedroom_group")
    assert state is not None
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ENTITY_ID) == [
        LIVING_ROOM_FAN_ENTITY_ID,
        PERCENTAGE_FULL_FAN_ENTITY_ID,
    ]

    state = menuai.states.get("fan.nested_group")
    assert state is not None
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ENTITY_ID) == ["fan.bedroom_group"]

    # Test controlling the nested group
    async with asyncio.timeout(0.5):
        await menuai.services.async_call(
            FAN_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "fan.nested_group"},
            blocking=True,
        )
    assert menuai.states.get(LIVING_ROOM_FAN_ENTITY_ID).state == STATE_ON
    assert menuai.states.get(PERCENTAGE_FULL_FAN_ENTITY_ID).state == STATE_ON
    assert menuai.states.get("fan.bedroom_group").state == STATE_ON
    assert menuai.states.get("fan.nested_group").state == STATE_ON
