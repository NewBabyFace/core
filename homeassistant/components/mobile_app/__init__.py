"""Integrates Native Apps to MenuAI."""

from contextlib import suppress
from functools import partial
from typing import Any

from menuai.auth import EVENT_USER_REMOVED
from menuai.components import cloud, intent, notify as menuai_notify
from menuai.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_DEVICE_ID, CONF_WEBHOOK_ID, Platform
from menuai.core import Event, menuai
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    discovery,
)
from menuai.helpers.storage import Store
from menuai.helpers.typing import ConfigType

# Pre-import the platforms so they get loaded when the integration
# is imported as they are almost always going to be loaded and its
# cheaper to import them all at once.
from . import (  # noqa: F401
    binary_sensor as binary_sensor_pre_import,
    device_tracker as device_tracker_pre_import,
    notify as notify_pre_import,
    sensor as sensor_pre_import,
    websocket_api,
)
from .const import (
    ATTR_DEVICE_NAME,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_OS_VERSION,
    CONF_CLOUDHOOK_URL,
    CONF_USER_ID,
    DATA_CONFIG_ENTRIES,
    DATA_DELETED_IDS,
    DATA_DEVICES,
    DATA_PUSH_CHANNEL,
    DATA_STORE,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .helpers import savable_state
from .http_api import RegistrationsView
from .timers import async_handle_timer_event
from .util import async_create_cloud_hook, supports_push
from .webhook import handle_webhook

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the mobile app component."""
    store = Store[dict[str, Any]](menuai, STORAGE_VERSION, STORAGE_KEY)
    if (app_config := await store.async_load()) is None or not isinstance(
        app_config, dict
    ):
        app_config = {
            DATA_CONFIG_ENTRIES: {},
            DATA_DELETED_IDS: [],
        }

    menuai.data[DOMAIN] = {
        DATA_CONFIG_ENTRIES: {},
        DATA_DELETED_IDS: app_config.get(DATA_DELETED_IDS, []),
        DATA_DEVICES: {},
        DATA_PUSH_CHANNEL: {},
        DATA_STORE: store,
    }

    menuai.http.register_view(RegistrationsView())

    for deleted_id in menuai.data[DOMAIN][DATA_DELETED_IDS]:
        with suppress(ValueError):
            webhook_register(
                menuai, DOMAIN, "Deleted Webhook", deleted_id, handle_webhook
            )

    menuai.async_create_task(
        discovery.async_load_platform(menuai, Platform.NOTIFY, DOMAIN, {}, config),
        eager_start=True,
    )

    websocket_api.async_setup_commands(menuai)

    async def _handle_user_removed(event: Event) -> None:
        """Remove an entry when the user is removed."""
        user_id = event.data["user_id"]
        for entry in menuai.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_USER_ID] == user_id:
                await menuai.config_entries.async_remove(entry.entry_id)

    menuai.bus.async_listen(EVENT_USER_REMOVED, _handle_user_removed)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a mobile_app entry."""
    registration = entry.data

    webhook_id = registration[CONF_WEBHOOK_ID]

    menuai.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id] = entry

    device_registry = dr.async_get(menuai)

    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, registration[ATTR_DEVICE_ID])},
        manufacturer=registration[ATTR_MANUFACTURER],
        model=registration[ATTR_MODEL],
        name=registration[ATTR_DEVICE_NAME],
        sw_version=registration[ATTR_OS_VERSION],
    )

    menuai.data[DOMAIN][DATA_DEVICES][webhook_id] = device

    registration_name = f"Mobile App: {registration[ATTR_DEVICE_NAME]}"
    webhook_register(menuai, DOMAIN, registration_name, webhook_id, handle_webhook)

    async def manage_cloudhook(state: cloud.CloudConnectionState) -> None:
        if (
            state is cloud.CloudConnectionState.CLOUD_CONNECTED
            and CONF_CLOUDHOOK_URL not in entry.data
        ):
            await async_create_cloud_hook(menuai, webhook_id, entry)

    if cloud.async_is_logged_in(menuai):
        if (
            CONF_CLOUDHOOK_URL not in entry.data
            and cloud.async_active_subscription(menuai)
            and cloud.async_is_connected(menuai)
        ):
            await async_create_cloud_hook(menuai, webhook_id, entry)
    elif CONF_CLOUDHOOK_URL in entry.data:
        # If we have a cloudhook but no longer logged in to the cloud, remove it from the entry
        data = dict(entry.data)
        data.pop(CONF_CLOUDHOOK_URL)
        menuai.config_entries.async_update_entry(entry, data=data)

    entry.async_on_unload(cloud.async_listen_connection_change(menuai, manage_cloudhook))

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if supports_push(menuai, webhook_id):
        entry.async_on_unload(
            intent.async_register_timer_handler(
                menuai, device.id, partial(async_handle_timer_event, menuai, entry)
            )
        )

    await menuai_notify.async_reload(menuai, DOMAIN)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a mobile app entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    webhook_id = entry.data[CONF_WEBHOOK_ID]

    webhook_unregister(menuai, webhook_id)
    del menuai.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]
    del menuai.data[DOMAIN][DATA_DEVICES][webhook_id]
    await menuai_notify.async_reload(menuai, DOMAIN)

    return True


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Cleanup when entry is removed."""
    menuai.data[DOMAIN][DATA_DELETED_IDS].append(entry.data[CONF_WEBHOOK_ID])
    store = menuai.data[DOMAIN][DATA_STORE]
    await store.async_save(savable_state(menuai))

    if CONF_CLOUDHOOK_URL in entry.data:
        with suppress(cloud.CloudNotAvailable, ValueError):
            await cloud.async_delete_cloudhook(menuai, entry.data[CONF_WEBHOOK_ID])
