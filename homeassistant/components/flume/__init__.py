"""The flume integration."""

from __future__ import annotations

from pyflume import FlumeAuth, FlumeDeviceList
from requests import Session
from requests.exceptions import RequestException
import voluptuous as vol

from menuai.config_entries import ConfigEntryState
from menuai.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from menuai.core import (
    menuai,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.selector import ConfigEntrySelector

from .const import BASE_TOKEN_FILENAME, DOMAIN, PLATFORMS
from .coordinator import (
    FlumeConfigEntry,
    FlumeNotificationDataUpdateCoordinator,
    FlumeRuntimeData,
)

SERVICE_LIST_NOTIFICATIONS = "list_notifications"
CONF_CONFIG_ENTRY = "config_entry"
LIST_NOTIFICATIONS_SERVICE_SCHEMA = vol.All(
    {
        vol.Required(CONF_CONFIG_ENTRY): ConfigEntrySelector({"integration": DOMAIN}),
    },
)


def _setup_entry(
    menuai: menuai, entry: FlumeConfigEntry
) -> tuple[FlumeAuth, FlumeDeviceList, Session]:
    """Config entry set up in executor."""
    config = entry.data

    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    client_id = config[CONF_CLIENT_ID]
    client_secret = config[CONF_CLIENT_SECRET]
    flume_token_full_path = menuai.config.path(f"{BASE_TOKEN_FILENAME}-{username}")

    http_session = Session()

    try:
        flume_auth = FlumeAuth(
            username,
            password,
            client_id,
            client_secret,
            flume_token_file=flume_token_full_path,
            http_session=http_session,
        )
        flume_devices = FlumeDeviceList(flume_auth, http_session=http_session)
    except RequestException as ex:
        raise ConfigEntryNotReady from ex
    except Exception as ex:
        raise ConfigEntryAuthFailed from ex

    return flume_auth, flume_devices, http_session


async def async_setup_entry(menuai: menuai, entry: FlumeConfigEntry) -> bool:
    """Set up flume from a config entry."""

    flume_auth, flume_devices, http_session = await menuai.async_add_executor_job(
        _setup_entry, menuai, entry
    )
    notification_coordinator = FlumeNotificationDataUpdateCoordinator(
        menuai=menuai, config_entry=entry, auth=flume_auth
    )

    entry.runtime_data = FlumeRuntimeData(
        devices=flume_devices,
        auth=flume_auth,
        http_session=http_session,
        notifications_coordinator=notification_coordinator,
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    setup_service(menuai)

    return True


async def async_unload_entry(menuai: menuai, entry: FlumeConfigEntry) -> bool:
    """Unload a config entry."""
    entry.runtime_data.http_session.close()
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


def setup_service(menuai: menuai) -> None:
    """Add the services for the flume integration."""

    @callback
    def list_notifications(call: ServiceCall) -> ServiceResponse:
        """Return the user notifications."""
        entry_id: str = call.data[CONF_CONFIG_ENTRY]
        entry: FlumeConfigEntry | None = menuai.config_entries.async_get_entry(entry_id)
        if not entry:
            raise ValueError(f"Invalid config entry: {entry_id}")
        if not entry.state == ConfigEntryState.LOADED:
            raise ValueError(f"Config entry not loaded: {entry_id}")
        return {
            "notifications": entry.runtime_data.notifications_coordinator.notifications  # type: ignore[dict-item]
        }

    menuai.services.async_register(
        DOMAIN,
        SERVICE_LIST_NOTIFICATIONS,
        list_notifications,
        schema=LIST_NOTIFICATIONS_SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
