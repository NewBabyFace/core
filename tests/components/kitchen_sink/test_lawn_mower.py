"""The tests for the kitchen_sink lawn mower platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.kitchen_sink import DOMAIN
from menuai.components.lawn_mower import (
    DOMAIN as LAWN_MOWER_DOMAIN,
    SERVICE_DOCK,
    SERVICE_PAUSE,
    SERVICE_START_MOWING,
    LawnMowerActivity,
)
from menuai.const import ATTR_ENTITY_ID, EVENT_STATE_CHANGED, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_capture_events, async_mock_service

MOWER_SERVICE_ENTITY = "lawn_mower.mower_can_dock"


@pytest.fixture
async def lawn_mower_only() -> None:
    """Enable only the lawn mower platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.LAWN_MOWER],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, lawn_mower_only):
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


async def test_states(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test the expected lawn mower entities are added."""
    states = menuai.states.async_all()
    assert set(states) == snapshot


@pytest.mark.parametrize(
    ("entity", "service_call", "activity", "next_activity"),
    [
        (
            "lawn_mower.mower_can_mow",
            SERVICE_START_MOWING,
            LawnMowerActivity.DOCKED,
            LawnMowerActivity.MOWING,
        ),
        (
            "lawn_mower.mower_can_pause",
            SERVICE_PAUSE,
            LawnMowerActivity.DOCKED,
            LawnMowerActivity.PAUSED,
        ),
        (
            "lawn_mower.mower_is_paused",
            SERVICE_START_MOWING,
            LawnMowerActivity.PAUSED,
            LawnMowerActivity.MOWING,
        ),
        (
            "lawn_mower.mower_can_dock",
            SERVICE_DOCK,
            LawnMowerActivity.MOWING,
            LawnMowerActivity.DOCKED,
        ),
        (
            "lawn_mower.mower_can_return",
            SERVICE_DOCK,
            LawnMowerActivity.RETURNING,
            LawnMowerActivity.DOCKED,
        ),
    ],
)
async def test_mower(
    menuai: menuai,
    entity: str,
    service_call: str,
    activity: LawnMowerActivity,
    next_activity: LawnMowerActivity,
) -> None:
    """Test the activity states of a lawn mower."""
    state = menuai.states.get(entity)

    assert state.state == str(activity.value)
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LAWN_MOWER_DOMAIN, service_call, {ATTR_ENTITY_ID: entity}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == entity
    assert state_changes[0].data["new_state"].state == next_activity.value


@pytest.mark.parametrize(
    "service_call",
    [
        SERVICE_DOCK,
        SERVICE_START_MOWING,
        SERVICE_PAUSE,
    ],
)
async def test_service_calls_mocked(menuai: menuai, service_call) -> None:
    """Test the services of a lawn mower."""
    calls = async_mock_service(menuai, LAWN_MOWER_DOMAIN, service_call)
    await menuai.services.async_call(
        LAWN_MOWER_DOMAIN,
        service_call,
        {ATTR_ENTITY_ID: MOWER_SERVICE_ENTITY},
        blocking=True,
    )
    assert len(calls) == 1
