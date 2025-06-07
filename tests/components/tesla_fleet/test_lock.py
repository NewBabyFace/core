"""Test the Tesla Fleet lock platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import VehicleOffline

from menuai.components.lock import (
    DOMAIN as LOCK_DOMAIN,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    LockState,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from . import assert_entities, setup_platform
from .const import COMMAND_OK

from tests.common import MockConfigEntry


async def test_lock(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the lock entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.LOCK])
    assert_entities(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


async def test_lock_offline(
    menuai: menuai,
    mock_vehicle_data: AsyncMock,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the lock entities are correct when offline."""

    mock_vehicle_data.side_effect = VehicleOffline
    await setup_platform(menuai, normal_config_entry, [Platform.LOCK])
    state = menuai.states.get("lock.test_lock")
    assert state.state == STATE_UNKNOWN


async def test_lock_services(
    menuai: menuai,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the lock services work."""

    await setup_platform(menuai, normal_config_entry, [Platform.LOCK])

    entity_id = "lock.test_lock"

    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.door_lock",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_LOCK,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        state = menuai.states.get(entity_id)
        assert state.state == LockState.LOCKED
        call.assert_called_once()

    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.door_unlock",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        state = menuai.states.get(entity_id)
        assert state.state == LockState.UNLOCKED
        call.assert_called_once()

    entity_id = "lock.test_charge_cable_lock"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_LOCK,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    with patch(
        "tesla_fleet_api.tesla.VehicleFleet.charge_port_door_open",
        return_value=COMMAND_OK,
    ) as call:
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        state = menuai.states.get(entity_id)
        assert state.state == LockState.UNLOCKED
        call.assert_called_once()
