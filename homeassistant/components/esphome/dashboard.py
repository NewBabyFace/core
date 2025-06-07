"""Files to interact with an ESPHome dashboard."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from menuai.config_entries import SOURCE_REAUTH
from menuai.const import EVENT_menuai_STOP
from menuai.core import CALLBACK_TYPE, Event, menuai, callback
from menuai.helpers.menuaiio import is_menuaiio
from menuai.helpers.singleton import singleton
from menuai.helpers.storage import Store
from menuai.util.menuai_dict import menuaiKey

from .const import DOMAIN
from .coordinator import ESPHomeDashboardCoordinator

_LOGGER = logging.getLogger(__name__)


KEY_DASHBOARD_MANAGER: menuaiKey[ESPHomeDashboardManager] = menuaiKey(
    "esphome_dashboard_manager"
)

STORAGE_KEY = "esphome.dashboard"
STORAGE_VERSION = 1


async def async_setup(menuai: menuai) -> None:
    """Set up the ESPHome dashboard."""
    # Try to restore the dashboard manager from storage
    # to avoid reloading every ESPHome config entry after
    # MenuAI starts and the dashboard is discovered.
    await async_get_or_create_dashboard_manager(menuai)


@singleton(KEY_DASHBOARD_MANAGER, async_=True)
async def async_get_or_create_dashboard_manager(
    menuai: menuai,
) -> ESPHomeDashboardManager:
    """Get the dashboard manager or create it."""
    manager = ESPHomeDashboardManager(menuai)
    await manager.async_setup()
    return manager


class ESPHomeDashboardManager:
    """Class to manage the dashboard and restore it from storage."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize the dashboard manager."""
        self._menuai = menuai
        self._store: Store[dict[str, Any]] = Store(menuai, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] | None = None
        self._current_dashboard: ESPHomeDashboardCoordinator | None = None
        self._cancel_shutdown: CALLBACK_TYPE | None = None

    async def async_setup(self) -> None:
        """Restore the dashboard from storage."""
        self._data = await self._store.async_load()
        if not (data := self._data) or not (info := data.get("info")):
            return
        if is_menuaiio(self._menuai):
            from menuai.components.menuaiio import (  # pylint: disable=import-outside-toplevel
                get_addons_info,
            )

            if (addons := get_addons_info(self._menuai)) is not None and info[
                "addon_slug"
            ] not in addons:
                # The addon is not installed anymore, but it make come back
                # so we don't want to remove the dashboard, but for now
                # we don't want to use it.
                _LOGGER.debug("Addon %s is no longer installed", info["addon_slug"])
                return

        await self.async_set_dashboard_info(
            info["addon_slug"], info["host"], info["port"]
        )

    @callback
    def async_get(self) -> ESPHomeDashboardCoordinator | None:
        """Get the current dashboard."""
        return self._current_dashboard

    async def async_set_dashboard_info(
        self, addon_slug: str, host: str, port: int
    ) -> None:
        """Set the dashboard info."""
        url = f"http://{host}:{port}"
        menuai = self._menuai

        if cur_dashboard := self._current_dashboard:
            if cur_dashboard.addon_slug == addon_slug and cur_dashboard.url == url:
                # Do nothing if we already have this data.
                return
            # Clear and make way for new dashboard
            await cur_dashboard.async_shutdown()
            if self._cancel_shutdown is not None:
                self._cancel_shutdown()
                self._cancel_shutdown = None
            self._current_dashboard = None

        dashboard = ESPHomeDashboardCoordinator(menuai, addon_slug, url)
        await dashboard.async_request_refresh()

        self._current_dashboard = dashboard

        async def on_menuai_stop(_: Event) -> None:
            await dashboard.async_shutdown()

        self._cancel_shutdown = menuai.bus.async_listen_once(
            EVENT_menuai_STOP, on_menuai_stop
        )

        new_data = {"info": {"addon_slug": addon_slug, "host": host, "port": port}}
        if self._data != new_data:
            await self._store.async_save(new_data)

        reloads = [
            menuai.config_entries.async_reload(entry.entry_id)
            for entry in menuai.config_entries.async_loaded_entries(DOMAIN)
        ]
        # Re-auth flows will check the dashboard for encryption key when the form is requested
        # but we only trigger reauth if the dashboard is available.
        if dashboard.last_update_success:
            reauths = [
                menuai.config_entries.flow.async_configure(flow["flow_id"])
                for flow in menuai.config_entries.flow.async_progress()
                if flow["handler"] == DOMAIN
                and flow["context"]["source"] == SOURCE_REAUTH
            ]
        else:
            reauths = []
            _LOGGER.error(
                "Dashboard unavailable; skipping reauth: %s", dashboard.last_exception
            )

        _LOGGER.debug(
            "Reloading %d and re-authenticating %d", len(reloads), len(reauths)
        )
        if reloads or reauths:
            await asyncio.gather(*reloads, *reauths)


@callback
def async_get_dashboard(menuai: menuai) -> ESPHomeDashboardCoordinator | None:
    """Get an instance of the dashboard if set.

    This is only safe to call after `async_setup` has been completed.

    It should not be called from the config flow because there is a race
    where manager can be an asyncio.Event instead of the actual manager
    because the singleton decorator is not yet done.
    """
    manager = menuai.data.get(KEY_DASHBOARD_MANAGER)
    return manager.async_get() if manager else None


async def async_set_dashboard_info(
    menuai: menuai, addon_slug: str, host: str, port: int
) -> None:
    """Set the dashboard info."""
    manager = await async_get_or_create_dashboard_manager(menuai)
    await manager.async_set_dashboard_info(addon_slug, host, port)
