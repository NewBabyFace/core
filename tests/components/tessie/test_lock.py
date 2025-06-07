"""Test the Tessie lock platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    LockState,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from .common import assert_entities, setup_platform


async def test_locks(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the lock entity is correct."""

    entry = await setup_platform(menuai, [Platform.LOCK])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    # Test lock set value functions
    entity_id = "lock.test_lock"
    with patch("menuai.components.tessie.lock.lock") as mock_run:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_LOCK,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_run.assert_called_once()
    assert menuai.states.get(entity_id).state == LockState.LOCKED

    with patch("menuai.components.tessie.lock.unlock") as mock_run:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_run.assert_called_once()
    assert menuai.states.get(entity_id).state == LockState.UNLOCKED

    # Test charge cable lock set value functions
    entity_id = "lock.test_charge_cable_lock"
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_LOCK,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )

    with patch(
        "menuai.components.tessie.lock.open_unlock_charge_port"
    ) as mock_run:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        assert menuai.states.get(entity_id).state == LockState.UNLOCKED
        mock_run.assert_called_once()
