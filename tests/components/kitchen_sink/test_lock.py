"""The tests for the kitchen_sink lock platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.kitchen_sink import DOMAIN
from menuai.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
    LockState,
)
from menuai.const import ATTR_ENTITY_ID, EVENT_STATE_CHANGED, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_capture_events, async_mock_service

LOCKED_LOCK = "lock.basic_lock"
OPENABLE_LOCK = "lock.openable_lock"
UNLOCKED_LOCK = "lock.another_basic_lock"


@pytest.fixture
async def lock_only() -> None:
    """Enable only the lock platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.LOCK],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, lock_only):
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


async def test_states(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test the expected lock entities are added."""
    states = menuai.states.async_all()
    assert set(states) == snapshot


async def test_locking(menuai: menuai) -> None:
    """Test the locking of a lock."""
    state = menuai.states.get(UNLOCKED_LOCK)
    assert state.state == LockState.UNLOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_LOCK, {ATTR_ENTITY_ID: UNLOCKED_LOCK}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == UNLOCKED_LOCK
    assert state_changes[0].data["new_state"].state == LockState.LOCKING

    assert state_changes[1].data["entity_id"] == UNLOCKED_LOCK
    assert state_changes[1].data["new_state"].state == LockState.LOCKED


async def test_unlocking(menuai: menuai) -> None:
    """Test the unlocking of a lock."""
    state = menuai.states.get(LOCKED_LOCK)
    assert state.state == LockState.LOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_UNLOCK, {ATTR_ENTITY_ID: LOCKED_LOCK}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == LOCKED_LOCK
    assert state_changes[0].data["new_state"].state == LockState.UNLOCKING

    assert state_changes[1].data["entity_id"] == LOCKED_LOCK
    assert state_changes[1].data["new_state"].state == LockState.UNLOCKED


async def test_opening_mocked(menuai: menuai) -> None:
    """Test the opening of a lock."""
    calls = async_mock_service(menuai, LOCK_DOMAIN, SERVICE_OPEN)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_OPEN, {ATTR_ENTITY_ID: OPENABLE_LOCK}, blocking=True
    )
    assert len(calls) == 1


async def test_opening(menuai: menuai) -> None:
    """Test the opening of a lock."""
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_OPEN, {ATTR_ENTITY_ID: OPENABLE_LOCK}, blocking=True
    )
    state = menuai.states.get(OPENABLE_LOCK)
    assert state.state == LockState.OPEN
