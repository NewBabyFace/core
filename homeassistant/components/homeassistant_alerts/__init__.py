"""The MenuAI alerts integration."""

from __future__ import annotations

import logging

from menuai.const import EVENT_COMPONENT_LOADED
from menuai.core import Event, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.debounce import Debouncer
from menuai.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from menuai.helpers.start import async_at_started
from menuai.helpers.typing import ConfigType
from menuai.setup import EventComponentLoaded

from .const import COMPONENT_LOADED_COOLDOWN, DOMAIN, REQUEST_TIMEOUT
from .coordinator import AlertUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up alerts."""
    last_alerts: dict[str, str | None] = {}

    async def async_update_alerts() -> None:
        nonlocal last_alerts

        active_alerts: dict[str, str | None] = {}

        for issue_id, alert in coordinator.data.items():
            # Skip creation if already created and not updated since then
            if issue_id in last_alerts and alert.date_updated == last_alerts[issue_id]:
                active_alerts[issue_id] = alert.date_updated
                continue

            # Fetch alert to get title + description
            try:
                response = await async_get_clientsession(menuai).get(
                    f"https://alerts.home-assistant.io/alerts/{alert.alert_id}.json",
                    timeout=REQUEST_TIMEOUT,
                )
            except TimeoutError:
                _LOGGER.warning("Error fetching %s: timeout", alert.filename)
                continue

            alert_content = await response.json()
            async_create_issue(
                menuai,
                DOMAIN,
                issue_id,
                is_fixable=False,
                issue_domain=alert.integration,
                severity=IssueSeverity.WARNING,
                translation_key="alert",
                translation_placeholders={
                    "title": alert_content["title"],
                    "description": alert_content["content"],
                },
            )
            active_alerts[issue_id] = alert.date_updated

        inactive_alerts = last_alerts.keys() - active_alerts.keys()
        for issue_id in inactive_alerts:
            async_delete_issue(menuai, DOMAIN, issue_id)

        last_alerts = active_alerts

    @callback
    def async_schedule_update_alerts() -> None:
        if not coordinator.last_update_success:
            return

        menuai.async_create_background_task(
            async_update_alerts(), "menuai_alerts update", eager_start=True
        )

    coordinator = AlertUpdateCoordinator(menuai)
    coordinator.async_add_listener(async_schedule_update_alerts)

    async def initial_refresh(menuai: menuai) -> None:
        refresh_debouncer = Debouncer(
            menuai,
            _LOGGER,
            cooldown=COMPONENT_LOADED_COOLDOWN,
            immediate=False,
            function=coordinator.async_refresh,
            background=True,
        )

        @callback
        def _component_loaded(_: Event[EventComponentLoaded]) -> None:
            refresh_debouncer.async_schedule_call()

        await coordinator.async_refresh()
        menuai.bus.async_listen(EVENT_COMPONENT_LOADED, _component_loaded)

    async_at_started(menuai, initial_refresh)

    return True
