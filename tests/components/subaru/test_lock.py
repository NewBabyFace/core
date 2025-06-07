"""Test Subaru locks."""

from unittest.mock import patch

import pytest
from voluptuous.error import MultipleInvalid

from menuai.components.lock import DOMAIN as LOCK_DOMAIN
from menuai.components.subaru.const import (
    ATTR_DOOR,
    DOMAIN,
    SERVICE_UNLOCK_SPECIFIC_DOOR,
    UNLOCK_DOOR_DRIVERS,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_LOCK, SERVICE_UNLOCK
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .conftest import MOCK_API

MOCK_API_LOCK = f"{MOCK_API}lock"
MOCK_API_UNLOCK = f"{MOCK_API}unlock"
DEVICE_ID = "lock.test_vehicle_2_door_locks"


async def test_device_exists(
    menuai: menuai, entity_registry: er.EntityRegistry, ev_entry
) -> None:
    """Test subaru lock entity exists."""
    entry = entity_registry.async_get(DEVICE_ID)
    assert entry


async def test_lock_cmd(menuai: menuai, ev_entry) -> None:
    """Test subaru lock function."""
    with patch(MOCK_API_LOCK) as mock_lock:
        await menuai.services.async_call(
            LOCK_DOMAIN, SERVICE_LOCK, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await menuai.async_block_till_done()
        mock_lock.assert_called_once()


async def test_unlock_cmd(menuai: menuai, ev_entry) -> None:
    """Test subaru unlock function."""
    with patch(MOCK_API_UNLOCK) as mock_unlock:
        await menuai.services.async_call(
            LOCK_DOMAIN, SERVICE_UNLOCK, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await menuai.async_block_till_done()
        mock_unlock.assert_called_once()


async def test_lock_cmd_fails(menuai: menuai, ev_entry) -> None:
    """Test subaru lock request that initiates but fails."""
    with (
        patch(MOCK_API_LOCK, return_value=False) as mock_lock,
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            LOCK_DOMAIN, SERVICE_UNLOCK, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
    mock_lock.assert_not_called()


async def test_unlock_specific_door(menuai: menuai, ev_entry) -> None:
    """Test subaru unlock specific door function."""
    with patch(MOCK_API_UNLOCK) as mock_unlock:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_UNLOCK_SPECIFIC_DOOR,
            {ATTR_ENTITY_ID: DEVICE_ID, ATTR_DOOR: UNLOCK_DOOR_DRIVERS},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_unlock.assert_called_once()


async def test_unlock_specific_door_invalid(menuai: menuai, ev_entry) -> None:
    """Test subaru unlock specific door function."""
    with patch(MOCK_API_UNLOCK) as mock_unlock, pytest.raises(MultipleInvalid):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_UNLOCK_SPECIFIC_DOOR,
            {ATTR_ENTITY_ID: DEVICE_ID, ATTR_DOOR: "bad_value"},
            blocking=True,
        )
    mock_unlock.assert_not_called()
