"""The tests for the backup helpers."""

import asyncio
from unittest.mock import patch

import pytest

from menuai.components.backup import DOMAIN as BACKUP_DOMAIN
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import backup as backup_helper
from menuai.setup import async_setup_component


async def test_async_get_manager(menuai: menuai) -> None:
    """Test async_get_manager."""
    backup_helper.async_initialize_backup(menuai)
    task = asyncio.create_task(backup_helper.async_get_manager(menuai))
    assert await async_setup_component(menuai, BACKUP_DOMAIN, {})
    await menuai.async_block_till_done()
    manager = await task
    assert manager is menuai.data[backup_helper.DATA_MANAGER]


async def test_async_get_manager_no_backup(menuai: menuai) -> None:
    """Test async_get_manager when the backup integration is not enabled."""
    with pytest.raises(menuaiError, match="Backup integration is not available"):
        await backup_helper.async_get_manager(menuai)


async def test_async_get_manager_backup_failed_setup(menuai: menuai) -> None:
    """Test test_async_get_manager when the backup integration can't be set up."""
    backup_helper.async_initialize_backup(menuai)

    with patch(
        "menuai.components.backup.manager.BackupManager.async_setup",
        side_effect=Exception("Boom!"),
    ):
        assert not await async_setup_component(menuai, BACKUP_DOMAIN, {})
    with pytest.raises(Exception, match="Boom!"):
        await backup_helper.async_get_manager(menuai)
