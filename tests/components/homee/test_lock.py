"""Test Homee locks."""

from unittest.mock import MagicMock, patch

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
from menuai.helpers import entity_registry as er

from . import build_mock_node, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def setup_lock(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_homee: MagicMock
) -> None:
    """Setups the integration lock tests."""
    mock_homee.nodes = [build_mock_node("lock.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)


@pytest.mark.parametrize(
    ("service", "target_value"),
    [
        (SERVICE_LOCK, 1),
        (SERVICE_UNLOCK, 0),
    ],
)
async def test_lock_services(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homee: MagicMock,
    service: str,
    target_value: int,
) -> None:
    """Test lock services."""
    await setup_lock(menuai, mock_config_entry, mock_homee)

    await menuai.services.async_call(
        LOCK_DOMAIN,
        service,
        {ATTR_ENTITY_ID: "lock.test_lock"},
    )
    mock_homee.set_value.assert_called_once_with(1, 1, target_value)


@pytest.mark.parametrize(
    ("target_value", "current_value", "expected"),
    [
        (1.0, 1.0, LockState.LOCKED),
        (0.0, 0.0, LockState.UNLOCKED),
        (1.0, 0.0, LockState.LOCKING),
        (0.0, 1.0, LockState.UNLOCKING),
    ],
)
async def test_lock_state(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homee: MagicMock,
    target_value: float,
    current_value: float,
    expected: LockState,
) -> None:
    """Test lock state."""
    mock_homee.nodes = [build_mock_node("lock.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    attribute = mock_homee.nodes[0].attributes[0]
    attribute.target_value = target_value
    attribute.current_value = current_value
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("lock.test_lock").state == expected


@pytest.mark.parametrize(
    ("attr_changed_by", "changed_by_id", "expected"),
    [
        (1, 0, "itself-0"),
        (2, 1, "user-testuser"),
        (3, 54, "homeegram-54"),
        (6, 0, "ai-0"),
    ],
)
async def test_lock_changed_by(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homee: MagicMock,
    attr_changed_by: int,
    changed_by_id: int,
    expected: str,
) -> None:
    """Test lock changed by entries."""
    mock_homee.nodes = [build_mock_node("lock.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    mock_homee.get_user_by_id.return_value = MagicMock(username="testuser")
    attribute = mock_homee.nodes[0].attributes[0]
    attribute.changed_by = attr_changed_by
    attribute.changed_by_id = changed_by_id
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("lock.test_lock").attributes["changed_by"] == expected


async def test_lock_snapshot(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homee: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the lock snapshots."""
    with patch("menuai.components.homee.PLATFORMS", [Platform.LOCK]):
        await setup_lock(menuai, mock_config_entry, mock_homee)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
