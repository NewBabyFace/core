"""Test schlage lock."""

from datetime import timedelta
from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory

from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockState
from menuai.const import ATTR_ENTITY_ID, SERVICE_LOCK, SERVICE_UNLOCK
from menuai.core import menuai

from . import MockSchlageConfigEntry

from tests.common import async_fire_time_changed


async def test_lock_attributes(
    menuai: menuai,
    mock_added_config_entry: MockSchlageConfigEntry,
    mock_schlage: Mock,
    mock_lock: Mock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test lock attributes."""
    lock = menuai.states.get("lock.vault_door")
    assert lock is not None
    assert lock.state == LockState.UNLOCKED
    assert lock.attributes["changed_by"] == "thumbturn"

    mock_lock.is_locked = False
    mock_lock.is_jammed = True
    # Make the coordinator refresh data.
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)
    lock = menuai.states.get("lock.vault_door")
    assert lock is not None
    assert lock.state == LockState.JAMMED


async def test_lock_services(
    menuai: menuai,
    mock_lock: Mock,
    mock_added_config_entry: MockSchlageConfigEntry,
) -> None:
    """Test lock services."""
    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        service_data={ATTR_ENTITY_ID: "lock.vault_door"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    mock_lock.lock.assert_called_once_with()

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        service_data={ATTR_ENTITY_ID: "lock.vault_door"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    mock_lock.unlock.assert_called_once_with()

    await menuai.config_entries.async_unload(mock_added_config_entry.entry_id)


async def test_changed_by(
    menuai: menuai,
    mock_lock: Mock,
    mock_added_config_entry: MockSchlageConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test population of the changed_by attribute."""
    mock_lock.last_changed_by.reset_mock()
    mock_lock.last_changed_by.return_value = "access code - foo"

    # Make the coordinator refresh data.
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)
    mock_lock.last_changed_by.assert_called_with()

    lock_device = menuai.states.get("lock.vault_door")
    assert lock_device is not None
    assert lock_device.attributes.get("changed_by") == "access code - foo"
