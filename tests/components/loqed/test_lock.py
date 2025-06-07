"""Tests the lock platform of the Loqed integration."""

from loqedAPI import loqed

from menuai.components.lock import LockState
from menuai.components.loqed import LoqedDataCoordinator
from menuai.components.loqed.const import DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
)
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_lock_entity(
    menuai: menuai,
    integration: MockConfigEntry,
) -> None:
    """Test the lock entity."""
    entity_id = "lock.home"

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == LockState.UNLOCKED


async def test_lock_responds_to_bolt_state_updates(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Tests the lock responding to updates."""
    coordinator: LoqedDataCoordinator = menuai.data[DOMAIN][integration.entry_id]
    lock.bolt_state = "night_lock"
    coordinator.async_update_listeners()

    entity_id = "lock.home"

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == LockState.LOCKED


async def test_lock_transition_to_unlocked(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Tests the lock transitions to unlocked state."""

    entity_id = "lock.home"

    await menuai.services.async_call(
        "lock", SERVICE_UNLOCK, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await menuai.async_block_till_done()
    lock.unlock.assert_called()


async def test_lock_transition_to_locked(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Tests the lock transitions to locked state."""

    entity_id = "lock.home"

    await menuai.services.async_call(
        "lock", SERVICE_LOCK, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await menuai.async_block_till_done()
    lock.lock.assert_called()


async def test_lock_transition_to_open(
    menuai: menuai, integration: MockConfigEntry, lock: loqed.Lock
) -> None:
    """Tests the lock transitions to open state."""

    entity_id = "lock.home"

    await menuai.services.async_call(
        "lock", SERVICE_OPEN, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await menuai.async_block_till_done()
    lock.open.assert_called()
