"""Backup platform for the Recorder integration."""

from logging import getLogger

from menuai.core import CoreState, menuai
from menuai.exceptions import menuaiError

from .util import async_migration_in_progress, get_instance

_LOGGER = getLogger(__name__)


async def async_pre_backup(menuai: menuai) -> None:
    """Perform operations before a backup starts."""
    _LOGGER.info("Backup start notification, locking database for writes")
    instance = get_instance(menuai)
    if menuai.state is not CoreState.running:
        raise menuaiError("MenuAI is not running")
    if async_migration_in_progress(menuai):
        raise menuaiError("Database migration in progress")
    await instance.lock_database()


async def async_post_backup(menuai: menuai) -> None:
    """Perform operations after a backup finishes."""
    instance = get_instance(menuai)
    _LOGGER.info("Backup end notification, releasing write lock")
    if not instance.unlock_database():
        raise menuaiError("Could not release database write lock")
