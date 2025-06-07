"""Backup platform for the NEW_NAME integration."""

from menuai.core import menuai


async def async_pre_backup(menuai: menuai) -> None:
    """Perform operations before a backup starts."""


async def async_post_backup(menuai: menuai) -> None:
    """Perform operations after a backup finishes."""
