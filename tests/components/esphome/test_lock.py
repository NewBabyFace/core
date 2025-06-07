"""Test ESPHome locks."""

from unittest.mock import call

from aioesphomeapi import (
    APIClient,
    LockCommand,
    LockEntityState,
    LockInfo,
    LockState as ESPHomeLockState,
)

from menuai.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
    LockState,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from .conftest import MockGenericDeviceEntryType


async def test_lock_entity_no_open(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic lock entity that does not support open."""
    entity_info = [
        LockInfo(
            object_id="mylock",
            key=1,
            name="my lock",
            unique_id="my_lock",
            supports_open=False,
            requires_code=False,
        )
    ]
    states = [LockEntityState(key=1, state=ESPHomeLockState.UNLOCKING)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("lock.test_mylock")
    assert state is not None
    assert state.state == LockState.UNLOCKING

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.test_mylock"},
        blocking=True,
    )
    mock_client.lock_command.assert_has_calls([call(1, LockCommand.LOCK)])
    mock_client.lock_command.reset_mock()


async def test_lock_entity_start_locked(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic lock entity that does not support open."""
    entity_info = [
        LockInfo(
            object_id="mylock",
            key=1,
            name="my lock",
            unique_id="my_lock",
        )
    ]
    states = [LockEntityState(key=1, state=ESPHomeLockState.LOCKED)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("lock.test_mylock")
    assert state is not None
    assert state.state == LockState.LOCKED


async def test_lock_entity_supports_open(
    menuai: menuai,
    mock_client: APIClient,
    mock_generic_device_entry: MockGenericDeviceEntryType,
) -> None:
    """Test a generic lock entity that supports open."""
    entity_info = [
        LockInfo(
            object_id="mylock",
            key=1,
            name="my lock",
            unique_id="my_lock",
            supports_open=True,
            requires_code=True,
        )
    ]
    states = [LockEntityState(key=1, state=ESPHomeLockState.LOCKING)]
    user_service = []
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("lock.test_mylock")
    assert state is not None
    assert state.state == LockState.LOCKING

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.test_mylock"},
        blocking=True,
    )
    mock_client.lock_command.assert_has_calls([call(1, LockCommand.LOCK)])
    mock_client.lock_command.reset_mock()

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "lock.test_mylock"},
        blocking=True,
    )
    mock_client.lock_command.assert_has_calls([call(1, LockCommand.UNLOCK, None)])

    mock_client.lock_command.reset_mock()
    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_OPEN,
        {ATTR_ENTITY_ID: "lock.test_mylock"},
        blocking=True,
    )
    mock_client.lock_command.assert_has_calls([call(1, LockCommand.OPEN)])
