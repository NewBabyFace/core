"""The tests for the Demo lock platform."""

from unittest.mock import patch

import pytest

from menuai.components.demo import DOMAIN, lock as demo_lock
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

FRONT = "lock.front_door"
KITCHEN = "lock.kitchen_door"
POORLY_INSTALLED = "lock.poorly_installed_door"
OPENABLE_LOCK = "lock.openable_lock"


@pytest.fixture
async def lock_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.LOCK],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, lock_only: None):
    """Set up demo component."""
    assert await async_setup_component(
        menuai, LOCK_DOMAIN, {LOCK_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()


@patch.object(demo_lock, "LOCK_UNLOCK_DELAY", 0)
async def test_locking(menuai: menuai) -> None:
    """Test the locking of a lock."""
    state = menuai.states.get(KITCHEN)
    assert state.state == LockState.UNLOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_LOCK, {ATTR_ENTITY_ID: KITCHEN}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == KITCHEN
    assert state_changes[0].data["new_state"].state == LockState.LOCKING

    assert state_changes[1].data["entity_id"] == KITCHEN
    assert state_changes[1].data["new_state"].state == LockState.LOCKED


@patch.object(demo_lock, "LOCK_UNLOCK_DELAY", 0)
async def test_unlocking(menuai: menuai) -> None:
    """Test the unlocking of a lock."""
    state = menuai.states.get(FRONT)
    assert state.state == LockState.LOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_UNLOCK, {ATTR_ENTITY_ID: FRONT}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == FRONT
    assert state_changes[0].data["new_state"].state == LockState.UNLOCKING

    assert state_changes[1].data["entity_id"] == FRONT
    assert state_changes[1].data["new_state"].state == LockState.UNLOCKED


@patch.object(demo_lock, "LOCK_UNLOCK_DELAY", 0)
async def test_opening(menuai: menuai) -> None:
    """Test the opening of a lock."""
    state = menuai.states.get(OPENABLE_LOCK)
    assert state.state == LockState.LOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_OPEN, {ATTR_ENTITY_ID: OPENABLE_LOCK}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == OPENABLE_LOCK
    assert state_changes[0].data["new_state"].state == LockState.OPENING

    assert state_changes[1].data["entity_id"] == OPENABLE_LOCK
    assert state_changes[1].data["new_state"].state == LockState.OPEN


@patch.object(demo_lock, "LOCK_UNLOCK_DELAY", 0)
async def test_jammed_when_locking(menuai: menuai) -> None:
    """Test the locking of a lock jams."""
    state = menuai.states.get(POORLY_INSTALLED)
    assert state.state == LockState.UNLOCKED
    await menuai.async_block_till_done()

    state_changes = async_capture_events(menuai, EVENT_STATE_CHANGED)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_LOCK, {ATTR_ENTITY_ID: POORLY_INSTALLED}, blocking=False
    )
    await menuai.async_block_till_done()

    assert state_changes[0].data["entity_id"] == POORLY_INSTALLED
    assert state_changes[0].data["new_state"].state == LockState.LOCKING

    assert state_changes[1].data["entity_id"] == POORLY_INSTALLED
    assert state_changes[1].data["new_state"].state == LockState.JAMMED


async def test_opening_mocked(menuai: menuai) -> None:
    """Test the opening of a lock."""
    calls = async_mock_service(menuai, LOCK_DOMAIN, SERVICE_OPEN)
    await menuai.services.async_call(
        LOCK_DOMAIN, SERVICE_OPEN, {ATTR_ENTITY_ID: OPENABLE_LOCK}, blocking=True
    )
    assert len(calls) == 1
