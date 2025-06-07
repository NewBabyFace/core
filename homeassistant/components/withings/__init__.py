"""Support for the Withings API.

For more details about this platform, please refer to the documentation at
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from aiohttp.hdrs import METH_POST
from aiohttp.web import Request, Response
from aiowithings import NotificationCategory, WithingsClient
from aiowithings.exceptions import WithingsError
from aiowithings.util import to_enum
from yarl import URL

from menuai.components import cloud
from menuai.components.http import menuaiView
from menuai.components.webhook import (
    async_generate_id as webhook_generate_id,
    async_generate_url as webhook_generate_url,
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_ACCESS_TOKEN,
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from menuai.helpers.event import async_call_later

from .const import DEFAULT_TITLE, DOMAIN, LOGGER
from .coordinator import (
    WithingsActivityDataUpdateCoordinator,
    WithingsBedPresenceDataUpdateCoordinator,
    WithingsDataUpdateCoordinator,
    WithingsDeviceDataUpdateCoordinator,
    WithingsGoalsDataUpdateCoordinator,
    WithingsMeasurementDataUpdateCoordinator,
    WithingsSleepDataUpdateCoordinator,
    WithingsWorkoutDataUpdateCoordinator,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]

SUBSCRIBE_DELAY = timedelta(seconds=5)
UNSUBSCRIBE_DELAY = timedelta(seconds=1)
CONF_CLOUDHOOK_URL = "cloudhook_url"
type WithingsConfigEntry = ConfigEntry[WithingsData]


@dataclass(slots=True)
class WithingsData:
    """Dataclass to hold withings domain data."""

    client: WithingsClient
    measurement_coordinator: WithingsMeasurementDataUpdateCoordinator
    sleep_coordinator: WithingsSleepDataUpdateCoordinator
    bed_presence_coordinator: WithingsBedPresenceDataUpdateCoordinator
    goals_coordinator: WithingsGoalsDataUpdateCoordinator
    activity_coordinator: WithingsActivityDataUpdateCoordinator
    workout_coordinator: WithingsWorkoutDataUpdateCoordinator
    device_coordinator: WithingsDeviceDataUpdateCoordinator
    coordinators: set[WithingsDataUpdateCoordinator] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Collect all coordinators in a set."""
        self.coordinators = {
            self.measurement_coordinator,
            self.sleep_coordinator,
            self.bed_presence_coordinator,
            self.goals_coordinator,
            self.activity_coordinator,
            self.workout_coordinator,
            self.device_coordinator,
        }


async def async_setup_entry(menuai: menuai, entry: WithingsConfigEntry) -> bool:
    """Set up Withings from a config entry."""
    if CONF_WEBHOOK_ID not in entry.data or entry.unique_id is None:
        new_data = entry.data.copy()
        unique_id = str(entry.data[CONF_TOKEN]["userid"])
        if CONF_WEBHOOK_ID not in new_data:
            new_data[CONF_WEBHOOK_ID] = webhook_generate_id()

        menuai.config_entries.async_update_entry(
            entry, data=new_data, unique_id=unique_id
        )
    session = async_get_clientsession(menuai)
    client = WithingsClient(session=session)
    implementation = await async_get_config_entry_implementation(menuai, entry)
    oauth_session = OAuth2Session(menuai, entry, implementation)

    refresh_lock = asyncio.Lock()

    async def _refresh_token() -> str:
        async with refresh_lock:
            await oauth_session.async_ensure_token_valid()
            token = oauth_session.token[CONF_ACCESS_TOKEN]
            if TYPE_CHECKING:
                assert isinstance(token, str)
            return token

    client.refresh_token_function = _refresh_token
    withings_data = WithingsData(
        client=client,
        measurement_coordinator=WithingsMeasurementDataUpdateCoordinator(
            menuai, entry, client
        ),
        sleep_coordinator=WithingsSleepDataUpdateCoordinator(menuai, entry, client),
        bed_presence_coordinator=WithingsBedPresenceDataUpdateCoordinator(
            menuai, entry, client
        ),
        goals_coordinator=WithingsGoalsDataUpdateCoordinator(menuai, entry, client),
        activity_coordinator=WithingsActivityDataUpdateCoordinator(menuai, entry, client),
        workout_coordinator=WithingsWorkoutDataUpdateCoordinator(menuai, entry, client),
        device_coordinator=WithingsDeviceDataUpdateCoordinator(menuai, entry, client),
    )

    for coordinator in withings_data.coordinators:
        await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = withings_data

    webhook_manager = WithingsWebhookManager(menuai, entry)

    async def manage_cloudhook(state: cloud.CloudConnectionState) -> None:
        LOGGER.debug("Cloudconnection state changed to %s", state)
        if state is cloud.CloudConnectionState.CLOUD_CONNECTED:
            await webhook_manager.register_webhook(None)

        if state is cloud.CloudConnectionState.CLOUD_DISCONNECTED:
            await webhook_manager.unregister_webhook(None)
            entry.async_on_unload(
                async_call_later(menuai, 30, webhook_manager.register_webhook)
            )

    if cloud.async_active_subscription(menuai):
        if cloud.async_is_connected(menuai):
            entry.async_on_unload(
                async_call_later(menuai, 1, webhook_manager.register_webhook)
            )
        entry.async_on_unload(
            cloud.async_listen_connection_change(menuai, manage_cloudhook)
        )
    else:
        entry.async_on_unload(
            async_call_later(menuai, 1, webhook_manager.register_webhook)
        )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: WithingsConfigEntry) -> bool:
    """Unload Withings config entry."""
    webhook_unregister(menuai, entry.data[CONF_WEBHOOK_ID])

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_subscribe_webhooks(client: WithingsClient, webhook_url: str) -> None:
    """Subscribe to Withings webhooks."""
    await async_unsubscribe_webhooks(client)

    notification_to_subscribe = {
        NotificationCategory.WEIGHT,
        NotificationCategory.PRESSURE,
        NotificationCategory.ACTIVITY,
        NotificationCategory.SLEEP,
        NotificationCategory.IN_BED,
        NotificationCategory.OUT_BED,
    }

    for notification in notification_to_subscribe:
        LOGGER.debug(
            "Subscribing %s for %s in %s seconds",
            webhook_url,
            notification,
            SUBSCRIBE_DELAY.total_seconds(),
        )
        # Withings will HTTP HEAD the callback_url and needs some downtime
        # between each call or there is a higher chance of failure.
        await asyncio.sleep(SUBSCRIBE_DELAY.total_seconds())
        await client.subscribe_notification(webhook_url, notification)


class WithingsWebhookManager:
    """Manager that manages the Withings webhooks."""

    _webhooks_registered = False
    _register_lock = asyncio.Lock()

    def __init__(self, menuai: menuai, entry: WithingsConfigEntry) -> None:
        """Initialize webhook manager."""
        self.menuai = menuai
        self.entry = entry

    @property
    def withings_data(self) -> WithingsData:
        """Return Withings data."""
        return self.entry.runtime_data

    async def unregister_webhook(
        self,
        _: Any,
    ) -> None:
        """Unregister webhooks at Withings."""
        async with self._register_lock:
            LOGGER.debug(
                "Unregister Withings webhook (%s)", self.entry.data[CONF_WEBHOOK_ID]
            )
            webhook_unregister(self.menuai, self.entry.data[CONF_WEBHOOK_ID])
            for coordinator in self.withings_data.coordinators:
                coordinator.webhook_subscription_listener(False)
            self._webhooks_registered = False
            try:
                await async_unsubscribe_webhooks(self.withings_data.client)
            except WithingsError as ex:
                LOGGER.warning("Failed to unsubscribe from Withings webhook: %s", ex)

    async def register_webhook(
        self,
        _: Any,
    ) -> None:
        """Register webhooks at Withings."""
        async with self._register_lock:
            if self._webhooks_registered:
                return
            if cloud.async_active_subscription(self.menuai):
                webhook_url = await _async_cloudhook_generate_url(self.menuai, self.entry)
            else:
                webhook_url = webhook_generate_url(
                    self.menuai, self.entry.data[CONF_WEBHOOK_ID]
                )
            url = URL(webhook_url)
            if url.scheme != "https" or url.port != 443:
                LOGGER.warning(
                    "Webhook not registered - "
                    "https and port 443 is required to register the webhook"
                )
                return

            webhook_name = "Withings"
            if self.entry.title != DEFAULT_TITLE:
                webhook_name = f"{DEFAULT_TITLE} {self.entry.title}"

            webhook_register(
                self.menuai,
                DOMAIN,
                webhook_name,
                self.entry.data[CONF_WEBHOOK_ID],
                get_webhook_handler(self.withings_data),
                allowed_methods=[METH_POST],
            )
            LOGGER.debug("Registered Withings webhook at menuai: %s", webhook_url)

            await async_subscribe_webhooks(self.withings_data.client, webhook_url)
            for coordinator in self.withings_data.coordinators:
                coordinator.webhook_subscription_listener(True)
            LOGGER.debug("Registered Withings webhook at Withings: %s", webhook_url)
            self.entry.async_on_unload(
                self.menuai.bus.async_listen_once(
                    EVENT_menuai_STOP, self.unregister_webhook
                )
            )
            self._webhooks_registered = True


async def async_unsubscribe_webhooks(client: WithingsClient) -> None:
    """Unsubscribe to all Withings webhooks."""
    try:
        current_webhooks = await client.list_notification_configurations()
    except ClientError:
        LOGGER.exception("Error when unsubscribing webhooks")
        return

    for webhook_configuration in current_webhooks:
        LOGGER.debug(
            "Unsubscribing %s for %s in %s seconds",
            webhook_configuration.callback_url,
            webhook_configuration.notification_category,
            UNSUBSCRIBE_DELAY.total_seconds(),
        )
        # Quick calls to Withings can result in the service returning errors.
        # Give them some time to cool down.
        await asyncio.sleep(UNSUBSCRIBE_DELAY.total_seconds())
        await client.revoke_notification_configurations(
            webhook_configuration.callback_url,
            webhook_configuration.notification_category,
        )


async def _async_cloudhook_generate_url(
    menuai: menuai, entry: WithingsConfigEntry
) -> str:
    """Generate the full URL for a webhook_id."""
    if CONF_CLOUDHOOK_URL not in entry.data:
        webhook_id = entry.data[CONF_WEBHOOK_ID]
        # Some users already have their webhook as cloudhook.
        # We remove them to be sure we can create a new one.
        with contextlib.suppress(ValueError):
            await cloud.async_delete_cloudhook(menuai, webhook_id)
        webhook_url = await cloud.async_create_cloudhook(menuai, webhook_id)
        data = {**entry.data, CONF_CLOUDHOOK_URL: webhook_url}
        menuai.config_entries.async_update_entry(entry, data=data)
        return webhook_url
    return str(entry.data[CONF_CLOUDHOOK_URL])


async def async_remove_entry(menuai: menuai, entry: WithingsConfigEntry) -> None:
    """Cleanup when entry is removed."""
    if cloud.async_active_subscription(menuai):
        try:
            LOGGER.debug(
                "Removing Withings cloudhook (%s)", entry.data[CONF_WEBHOOK_ID]
            )
            await cloud.async_delete_cloudhook(menuai, entry.data[CONF_WEBHOOK_ID])
        except cloud.CloudNotAvailable:
            pass


def json_message_response(message: str, message_code: int) -> Response:
    """Produce common json output."""
    return menuaiView.json({"message": message, "code": message_code})


def get_webhook_handler(
    withings_data: WithingsData,
) -> Callable[[menuai, str, Request], Awaitable[Response | None]]:
    """Return webhook handler."""

    async def async_webhook_handler(
        menuai: menuai, webhook_id: str, request: Request
    ) -> Response | None:
        # Handle http post calls to the path.
        if not request.body_exists:
            return json_message_response("No request body", message_code=12)

        params = await request.post()

        if "appli" not in params:
            return json_message_response(
                "Parameter appli not provided", message_code=20
            )

        notification_category = to_enum(
            NotificationCategory,
            int(params.getone("appli")),  # type: ignore[arg-type]
            NotificationCategory.UNKNOWN,
        )

        for coordinator in withings_data.coordinators:
            if notification_category in coordinator.notification_categories:
                await coordinator.async_webhook_data_updated(notification_category)

        return json_message_response("Success", message_code=0)

    return async_webhook_handler
