"""The tests for the group cover platform."""

import asyncio
from datetime import timedelta
from typing import Any

import pytest

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverState,
)
from menuai.components.group.cover import DEFAULT_NAME
from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITIES,
    CONF_UNIQUE_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_STOP_COVER_TILT,
    SERVICE_TOGGLE,
    SERVICE_TOGGLE_COVER_TILT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import assert_setup_component, async_fire_time_changed

COVER_GROUP = "cover.cover_group"
DEMO_COVER = "cover.kitchen_window"
DEMO_COVER_POS = "cover.hall_window"
DEMO_COVER_TILT = "cover.living_room_window"
DEMO_TILT = "cover.tilt_demo"

CONFIG_ALL = {
    COVER_DOMAIN: [
        {"platform": "demo"},
        {
            "platform": "group",
            CONF_ENTITIES: [DEMO_COVER, DEMO_COVER_POS, DEMO_COVER_TILT, DEMO_TILT],
        },
    ]
}

CONFIG_POS = {
    COVER_DOMAIN: [
        {"platform": "demo"},
        {
            "platform": "group",
            CONF_ENTITIES: [DEMO_COVER_POS, DEMO_COVER_TILT, DEMO_TILT],
        },
    ]
}

CONFIG_TILT_ONLY = {
    COVER_DOMAIN: [
        {"platform": "demo"},
        {
            "platform": "group",
            CONF_ENTITIES: [DEMO_COVER_TILT, DEMO_TILT],
        },
    ]
}

CONFIG_ATTRIBUTES = {
    COVER_DOMAIN: {
        "platform": "group",
        CONF_ENTITIES: [DEMO_COVER, DEMO_COVER_POS, DEMO_COVER_TILT, DEMO_TILT],
        CONF_UNIQUE_ID: "unique_identifier",
    }
}


@pytest.fixture
async def setup_comp(
    menuai: menuai, config_count: tuple[dict[str, Any], int]
) -> None:
    """Set up group cover component."""
    config, count = config_count
    with assert_setup_component(count, COVER_DOMAIN):
        await async_setup_component(menuai, COVER_DOMAIN, config)
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()


@pytest.mark.parametrize("config_count", [(CONFIG_ATTRIBUTES, 1)])
@pytest.mark.usefixtures("setup_comp")
async def test_state(menuai: menuai) -> None:
    """Test handling of state.

    The group state is unknown if all group members are unknown or unavailable.
    Otherwise, the group state is opening if at least one group member is opening.
    Otherwise, the group state is closing if at least one group member is closing.
    Otherwise, the group state is open if at least one group member is open.
    Otherwise, the group state is closed.
    """
    state = menuai.states.get(COVER_GROUP)
    # No entity has a valid state -> group state unavailable
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert ATTR_ENTITY_ID not in state.attributes
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Test group members exposed as attribute
    menuai.states.async_set(DEMO_COVER, STATE_UNKNOWN, {})
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_GROUP)
    assert state.attributes[ATTR_ENTITY_ID] == [
        DEMO_COVER,
        DEMO_COVER_POS,
        DEMO_COVER_TILT,
        DEMO_TILT,
    ]

    # The group state is unavailable if all group members are unavailable.
    menuai.states.async_set(DEMO_COVER, STATE_UNAVAILABLE, {})
    menuai.states.async_set(DEMO_COVER_POS, STATE_UNAVAILABLE, {})
    menuai.states.async_set(DEMO_COVER_TILT, STATE_UNAVAILABLE, {})
    menuai.states.async_set(DEMO_TILT, STATE_UNAVAILABLE, {})
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_GROUP)
    assert state.state == STATE_UNAVAILABLE

    # The group state is unknown if all group members are unknown or unavailable.
    for state_1 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        for state_2 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            for state_3 in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                menuai.states.async_set(DEMO_COVER, state_1, {})
                menuai.states.async_set(DEMO_COVER_POS, state_2, {})
                menuai.states.async_set(DEMO_COVER_TILT, state_3, {})
                menuai.states.async_set(DEMO_TILT, STATE_UNKNOWN, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(COVER_GROUP)
                assert state.state == STATE_UNKNOWN

    # At least one member opening -> group opening
    for state_1 in (
        CoverState.CLOSED,
        CoverState.CLOSING,
        CoverState.OPEN,
        CoverState.OPENING,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    ):
        for state_2 in (
            CoverState.CLOSED,
            CoverState.CLOSING,
            CoverState.OPEN,
            CoverState.OPENING,
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            for state_3 in (
                CoverState.CLOSED,
                CoverState.CLOSING,
                CoverState.OPEN,
                CoverState.OPENING,
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                menuai.states.async_set(DEMO_COVER, state_1, {})
                menuai.states.async_set(DEMO_COVER_POS, state_2, {})
                menuai.states.async_set(DEMO_COVER_TILT, state_3, {})
                menuai.states.async_set(DEMO_TILT, CoverState.OPENING, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(COVER_GROUP)
                assert state.state == CoverState.OPENING

    # At least one member closing -> group closing
    for state_1 in (
        CoverState.CLOSED,
        CoverState.CLOSING,
        CoverState.OPEN,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    ):
        for state_2 in (
            CoverState.CLOSED,
            CoverState.CLOSING,
            CoverState.OPEN,
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            for state_3 in (
                CoverState.CLOSED,
                CoverState.CLOSING,
                CoverState.OPEN,
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                menuai.states.async_set(DEMO_COVER, state_1, {})
                menuai.states.async_set(DEMO_COVER_POS, state_2, {})
                menuai.states.async_set(DEMO_COVER_TILT, state_3, {})
                menuai.states.async_set(DEMO_TILT, CoverState.CLOSING, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(COVER_GROUP)
                assert state.state == CoverState.CLOSING

    # At least one member open -> group open
    for state_1 in (
        CoverState.CLOSED,
        CoverState.OPEN,
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    ):
        for state_2 in (
            CoverState.CLOSED,
            CoverState.OPEN,
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            for state_3 in (
                CoverState.CLOSED,
                CoverState.OPEN,
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                menuai.states.async_set(DEMO_COVER, state_1, {})
                menuai.states.async_set(DEMO_COVER_POS, state_2, {})
                menuai.states.async_set(DEMO_COVER_TILT, state_3, {})
                menuai.states.async_set(DEMO_TILT, CoverState.OPEN, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(COVER_GROUP)
                assert state.state == CoverState.OPEN

    # At least one member closed -> group closed
    for state_1 in (CoverState.CLOSED, STATE_UNAVAILABLE, STATE_UNKNOWN):
        for state_2 in (CoverState.CLOSED, STATE_UNAVAILABLE, STATE_UNKNOWN):
            for state_3 in (CoverState.CLOSED, STATE_UNAVAILABLE, STATE_UNKNOWN):
                menuai.states.async_set(DEMO_COVER, state_1, {})
                menuai.states.async_set(DEMO_COVER_POS, state_2, {})
                menuai.states.async_set(DEMO_COVER_TILT, state_3, {})
                menuai.states.async_set(DEMO_TILT, CoverState.CLOSED, {})
                await menuai.async_block_till_done()
                state = menuai.states.get(COVER_GROUP)
                assert state.state == CoverState.CLOSED

    # All group members removed from the state machine -> unavailable
    menuai.states.async_remove(DEMO_COVER)
    menuai.states.async_remove(DEMO_COVER_POS)
    menuai.states.async_remove(DEMO_COVER_TILT)
    menuai.states.async_remove(DEMO_TILT)
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_GROUP)
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("config_count", [(CONFIG_ATTRIBUTES, 1)])
@pytest.mark.usefixtures("setup_comp")
async def test_attributes(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test handling of state attributes."""
    state = menuai.states.get(COVER_GROUP)
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert ATTR_ENTITY_ID not in state.attributes
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Set entity as closed
    menuai.states.async_set(DEMO_COVER, CoverState.CLOSED, {})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.CLOSED
    assert state.attributes[ATTR_ENTITY_ID] == [
        DEMO_COVER,
        DEMO_COVER_POS,
        DEMO_COVER_TILT,
        DEMO_TILT,
    ]

    # Set entity as opening
    menuai.states.async_set(DEMO_COVER, CoverState.OPENING, {})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPENING

    # Set entity as closing
    menuai.states.async_set(DEMO_COVER, CoverState.CLOSING, {})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.CLOSING

    # Set entity as unknown again
    menuai.states.async_set(DEMO_COVER, STATE_UNKNOWN, {})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == STATE_UNKNOWN

    # Add Entity that supports open / close / stop
    menuai.states.async_set(DEMO_COVER, CoverState.OPEN, {ATTR_SUPPORTED_FEATURES: 11})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 11
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Add Entity that supports set_cover_position
    menuai.states.async_set(
        DEMO_COVER_POS,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 4, ATTR_CURRENT_POSITION: 70},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 15
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Add Entity that supports open tilt / close tilt / stop tilt
    menuai.states.async_set(DEMO_TILT, CoverState.OPEN, {ATTR_SUPPORTED_FEATURES: 112})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 127
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Add Entity that supports set_tilt_position
    menuai.states.async_set(
        DEMO_COVER_TILT,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 128, ATTR_CURRENT_TILT_POSITION: 60},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 255
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 60

    # ### Test state when group members have different states ###
    # ##########################

    # Covers
    menuai.states.async_set(
        DEMO_COVER,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 4, ATTR_CURRENT_POSITION: 100},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 244
    assert state.attributes[ATTR_CURRENT_POSITION] == 85  # (70 + 100) / 2
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 60

    menuai.states.async_remove(DEMO_COVER)
    menuai.states.async_remove(DEMO_COVER_POS)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 240
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 60

    # Tilts
    menuai.states.async_set(
        DEMO_TILT,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 128, ATTR_CURRENT_TILT_POSITION: 100},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 128
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 80  # (60 + 100) / 2

    menuai.states.async_remove(DEMO_COVER_TILT)
    menuai.states.async_set(DEMO_TILT, CoverState.CLOSED)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.CLOSED
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 0
    assert ATTR_CURRENT_POSITION not in state.attributes
    assert ATTR_CURRENT_TILT_POSITION not in state.attributes

    # Group member has set assumed_state
    menuai.states.async_set(DEMO_TILT, CoverState.CLOSED, {ATTR_ASSUMED_STATE: True})
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert ATTR_ASSUMED_STATE not in state.attributes

    # Test entity registry integration
    entry = entity_registry.async_get(COVER_GROUP)
    assert entry
    assert entry.unique_id == "unique_identifier"


@pytest.mark.parametrize("config_count", [(CONFIG_TILT_ONLY, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_cover_that_only_supports_tilt_removed(menuai: menuai) -> None:
    """Test removing a cover that support tilt."""
    menuai.states.async_set(
        DEMO_COVER_TILT,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 128, ATTR_CURRENT_TILT_POSITION: 60},
    )
    menuai.states.async_set(
        DEMO_TILT,
        CoverState.OPEN,
        {ATTR_SUPPORTED_FEATURES: 128, ATTR_CURRENT_TILT_POSITION: 60},
    )
    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_FRIENDLY_NAME] == DEFAULT_NAME
    assert state.attributes[ATTR_ENTITY_ID] == [
        DEMO_COVER_TILT,
        DEMO_TILT,
    ]
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert ATTR_CURRENT_TILT_POSITION in state.attributes

    menuai.states.async_remove(DEMO_COVER_TILT)
    menuai.states.async_set(DEMO_TILT, CoverState.CLOSED)
    await menuai.async_block_till_done()


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_open_covers(menuai: menuai) -> None:
    """Test open cover function."""
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )

    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100

    assert menuai.states.get(DEMO_COVER).state == CoverState.OPEN
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 100
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 100


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_close_covers(menuai: menuai) -> None:
    """Test close cover function."""
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )

    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.CLOSED
    assert state.attributes[ATTR_CURRENT_POSITION] == 0

    assert menuai.states.get(DEMO_COVER).state == CoverState.CLOSED
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 0
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 0


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_toggle_covers(menuai: menuai) -> None:
    """Test toggle cover function."""
    # Start covers in open state
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN

    # Toggle will close covers
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.CLOSED
    assert state.attributes[ATTR_CURRENT_POSITION] == 0

    assert menuai.states.get(DEMO_COVER).state == CoverState.CLOSED
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 0
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 0

    # Toggle again will open covers
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100

    assert menuai.states.get(DEMO_COVER).state == CoverState.OPEN
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 100
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 100


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_stop_covers(menuai: menuai) -> None:
    """Test stop cover function."""
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_STOP_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPENING
    assert state.attributes[ATTR_CURRENT_POSITION] == 50  # (20 + 80) / 2

    assert menuai.states.get(DEMO_COVER).state == CoverState.OPEN
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 20
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 80


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_set_cover_position(menuai: menuai) -> None:
    """Test set cover position function."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: COVER_GROUP, ATTR_POSITION: 50},
        blocking=True,
    )
    for _ in range(4):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 50

    assert menuai.states.get(DEMO_COVER).state == CoverState.CLOSED
    assert menuai.states.get(DEMO_COVER_POS).attributes[ATTR_CURRENT_POSITION] == 50
    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_POSITION] == 50


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_open_tilts(menuai: menuai) -> None:
    """Test open tilt function."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    for _ in range(5):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100

    assert (
        menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 100
    )


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_close_tilts(menuai: menuai) -> None:
    """Test close tilt function."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    for _ in range(5):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0

    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 0


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_toggle_tilts(menuai: menuai) -> None:
    """Test toggle tilt function."""
    # Start tilted open
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100

    assert (
        menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 100
    )

    # Toggle will tilt closed
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0

    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 0

    # Toggle again will tilt open
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100

    assert (
        menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 100
    )


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_stop_tilts(menuai: menuai) -> None:
    """Test stop tilts function."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER_TILT,
        {ATTR_ENTITY_ID: COVER_GROUP},
        blocking=True,
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 60

    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 60


@pytest.mark.parametrize("config_count", [(CONFIG_ALL, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_set_tilt_positions(menuai: menuai) -> None:
    """Test set tilt position function."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: COVER_GROUP, ATTR_TILT_POSITION: 80},
        blocking=True,
    )
    for _ in range(3):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get(COVER_GROUP)
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 80

    assert menuai.states.get(DEMO_COVER_TILT).attributes[ATTR_CURRENT_TILT_POSITION] == 80


@pytest.mark.parametrize("config_count", [(CONFIG_POS, 2)])
@pytest.mark.usefixtures("setup_comp")
async def test_is_opening_closing(menuai: menuai) -> None:
    """Test is_opening property."""
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )
    await menuai.async_block_till_done()

    # Both covers opening -> opening
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.OPENING
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.OPENING
    assert menuai.states.get(COVER_GROUP).state == CoverState.OPENING

    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: COVER_GROUP}, blocking=True
    )

    # Both covers closing -> closing
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get(COVER_GROUP).state == CoverState.CLOSING

    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.OPENING, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()

    # Closing + Opening -> Opening
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.OPENING
    assert menuai.states.get(COVER_GROUP).state == CoverState.OPENING

    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.CLOSING, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()

    # Both covers closing -> closing
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.CLOSING
    assert menuai.states.get(COVER_GROUP).state == CoverState.CLOSING

    # Closed + Closing -> Closing
    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.CLOSED, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.CLOSED
    assert menuai.states.get(COVER_GROUP).state == CoverState.CLOSING

    # Open + Closing -> Closing
    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.OPEN, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.OPEN
    assert menuai.states.get(COVER_GROUP).state == CoverState.CLOSING

    # Closed + Opening -> Closing
    menuai.states.async_set(
        DEMO_COVER_TILT, CoverState.OPENING, {ATTR_SUPPORTED_FEATURES: 11}
    )
    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.CLOSED, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.OPENING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.CLOSED
    assert menuai.states.get(COVER_GROUP).state == CoverState.OPENING

    # Open + Opening -> Closing
    menuai.states.async_set(
        DEMO_COVER_POS, CoverState.OPEN, {ATTR_SUPPORTED_FEATURES: 11}
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.OPENING
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.OPEN
    assert menuai.states.get(COVER_GROUP).state == CoverState.OPENING


async def test_nested_group(menuai: menuai) -> None:
    """Test nested cover group."""
    await async_setup_component(
        menuai,
        COVER_DOMAIN,
        {
            COVER_DOMAIN: [
                {"platform": "demo"},
                {
                    "platform": "group",
                    "entities": ["cover.bedroom_group"],
                    "name": "Nested Group",
                },
                {
                    "platform": "group",
                    CONF_ENTITIES: [DEMO_COVER_POS, DEMO_COVER_TILT],
                    "name": "Bedroom Group",
                },
            ]
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("cover.bedroom_group")
    assert state is not None
    assert state.state == CoverState.OPEN
    assert state.attributes.get(ATTR_ENTITY_ID) == [DEMO_COVER_POS, DEMO_COVER_TILT]

    state = menuai.states.get("cover.nested_group")
    assert state is not None
    assert state.state == CoverState.OPEN
    assert state.attributes.get(ATTR_ENTITY_ID) == ["cover.bedroom_group"]

    # Test controlling the nested group
    async with asyncio.timeout(0.5):
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: "cover.nested_group"},
            blocking=True,
        )
    assert menuai.states.get(DEMO_COVER_POS).state == CoverState.CLOSING
    assert menuai.states.get(DEMO_COVER_TILT).state == CoverState.CLOSING
    assert menuai.states.get("cover.bedroom_group").state == CoverState.CLOSING
    assert menuai.states.get("cover.nested_group").state == CoverState.CLOSING
