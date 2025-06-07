"""Update helpers for Supervisor."""

from __future__ import annotations

from aiohasupervisor import SupervisorError
from aiohasupervisor.models import (
    menuaiUpdateOptions,
    OSUpdate,
    StoreAddonUpdate,
)

from menuai.core import menuai
from menuai.exceptions import menuaiError

from .handler import get_supervisor_client


async def update_addon(
    menuai: menuai,
    addon: str,
    backup: bool,
    addon_name: str | None,
    installed_version: str | None,
) -> None:
    """Update an addon.

    Optionally make a backup before updating.
    """
    client = get_supervisor_client(menuai)

    if backup:
        # pylint: disable-next=import-outside-toplevel
        from .backup import backup_addon_before_update

        await backup_addon_before_update(menuai, addon, addon_name, installed_version)

    try:
        await client.store.update_addon(addon, StoreAddonUpdate(backup=False))
    except SupervisorError as err:
        raise menuaiError(
            f"Error updating {addon_name or addon}: {err}"
        ) from err


async def update_core(menuai: menuai, version: str | None, backup: bool) -> None:
    """Update core.

    Optionally make a backup before updating.
    """
    client = get_supervisor_client(menuai)

    if backup:
        # pylint: disable-next=import-outside-toplevel
        from .backup import backup_core_before_update

        await backup_core_before_update(menuai)

    try:
        await client.menuai.update(
            menuaiUpdateOptions(version=version, backup=False)
        )
    except SupervisorError as err:
        raise menuaiError(f"Error updating MenuAI Core: {err}") from err


async def update_os(menuai: menuai, version: str | None, backup: bool) -> None:
    """Update OS.

    Optionally make a core backup before updating.
    """
    client = get_supervisor_client(menuai)

    if backup:
        # pylint: disable-next=import-outside-toplevel
        from .backup import backup_core_before_update

        await backup_core_before_update(menuai)

    try:
        await client.os.update(OSUpdate(version=version))
    except SupervisorError as err:
        raise menuaiError(
            f"Error updating MenuAI Operating System: {err}"
        ) from err
