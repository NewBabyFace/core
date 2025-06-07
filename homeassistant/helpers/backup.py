"""Helpers for the backup integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.components.backup import (
        BackupManager,
        BackupPlatformEvent,
        ManagerStateEvent,
    )

DATA_BACKUP: menuaiKey[BackupData] = menuaiKey("backup_data")
DATA_MANAGER: menuaiKey[BackupManager] = menuaiKey("backup")


@dataclass(slots=True)
class BackupData:
    """Backup data stored in menuai.data."""

    backup_event_subscriptions: list[Callable[[ManagerStateEvent], None]] = field(
        default_factory=list
    )
    backup_platform_event_subscriptions: list[Callable[[BackupPlatformEvent], None]] = (
        field(default_factory=list)
    )
    manager_ready: asyncio.Future[None] = field(default_factory=asyncio.Future)


@callback
def async_initialize_backup(menuai: menuai) -> None:
    """Initialize backup data.

    This creates the BackupData instance stored in menuai.data[DATA_BACKUP] and
    registers the basic backup websocket API which is used by frontend to subscribe
    to backup events.
    """
    # pylint: disable-next=import-outside-toplevel
    from menuai.components.backup import basic_websocket

    menuai.data[DATA_BACKUP] = BackupData()
    basic_websocket.async_register_websocket_handlers(menuai)


async def async_get_manager(menuai: menuai) -> BackupManager:
    """Get the backup manager instance.

    Raises menuaiError if the backup integration is not available.
    """
    if DATA_BACKUP not in menuai.data:
        raise menuaiError("Backup integration is not available")

    await menuai.data[DATA_BACKUP].manager_ready
    return menuai.data[DATA_MANAGER]


@callback
def async_subscribe_events(
    menuai: menuai,
    on_event: Callable[[ManagerStateEvent], None],
) -> Callable[[], None]:
    """Subscribe to backup events."""
    backup_event_subscriptions = menuai.data[DATA_BACKUP].backup_event_subscriptions

    def remove_subscription() -> None:
        backup_event_subscriptions.remove(on_event)

    backup_event_subscriptions.append(on_event)
    return remove_subscription


@callback
def async_subscribe_platform_events(
    menuai: menuai,
    on_event: Callable[[BackupPlatformEvent], None],
) -> Callable[[], None]:
    """Subscribe to backup platform events."""
    backup_platform_event_subscriptions = menuai.data[
        DATA_BACKUP
    ].backup_platform_event_subscriptions

    def remove_subscription() -> None:
        backup_platform_event_subscriptions.remove(on_event)

    backup_platform_event_subscriptions.append(on_event)
    return remove_subscription
