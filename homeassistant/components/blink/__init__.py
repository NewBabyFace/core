"""Support for Blink Home Camera System."""

from copy import deepcopy
import logging
from typing import Any

from aiohttp import ClientError
from blinkpy.auth import Auth
from blinkpy.blinkpy import Blink
import voluptuous as vol

from menuai.components import persistent_notification
from menuai.const import (
    CONF_FILE_PATH,
    CONF_FILENAME,
    CONF_NAME,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
)
from menuai.core import menuai, callback
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import BlinkConfigEntry, BlinkUpdateCoordinator
from .services import setup_services

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_VIDEO_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME): cv.string, vol.Required(CONF_FILENAME): cv.string}
)
SERVICE_SEND_PIN_SCHEMA = vol.Schema({vol.Optional(CONF_PIN): cv.string})
SERVICE_SAVE_RECENT_CLIPS_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME): cv.string, vol.Required(CONF_FILE_PATH): cv.string}
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def _reauth_flow_wrapper(
    menuai: menuai, entry: BlinkConfigEntry, data: dict[str, Any]
) -> None:
    """Reauth flow wrapper."""
    entry.async_start_reauth(menuai, data=data)
    persistent_notification.async_create(
        menuai,
        (
            "Blink configuration migrated to a new version. Please go to the"
            " integrations page to re-configure (such as sending a new 2FA key)."
        ),
        "Blink Migration",
    )


async def async_migrate_entry(menuai: menuai, entry: BlinkConfigEntry) -> bool:
    """Handle migration of a previous version config entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)
    data = {**entry.data}
    if entry.version == 1:
        data.pop("login_response", None)
        await _reauth_flow_wrapper(menuai, entry, data)
        return False
    if entry.version == 2:
        await _reauth_flow_wrapper(menuai, entry, data)
        return False
    return True


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Blink."""

    setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: BlinkConfigEntry) -> bool:
    """Set up Blink via config entry."""
    _async_import_options_from_data_if_missing(menuai, entry)
    session = async_get_clientsession(menuai)
    blink = Blink(session=session)
    auth_data = deepcopy(dict(entry.data))
    blink.auth = Auth(auth_data, no_prompt=True, session=session)
    blink.refresh_rate = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = BlinkUpdateCoordinator(menuai, entry, blink)

    try:
        await blink.start()
    except (ClientError, TimeoutError) as ex:
        raise ConfigEntryNotReady("Can not connect to host") from ex

    if blink.auth.check_key_required():
        _LOGGER.debug("Attempting a reauth flow")
        raise ConfigEntryAuthFailed("Need 2FA for Blink")

    if not blink.available:
        raise ConfigEntryNotReady

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


@callback
def _async_import_options_from_data_if_missing(
    menuai: menuai, entry: BlinkConfigEntry
) -> None:
    options = dict(entry.options)
    if CONF_SCAN_INTERVAL not in entry.options:
        options[CONF_SCAN_INTERVAL] = entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        menuai.config_entries.async_update_entry(entry, options=options)


async def async_unload_entry(menuai: menuai, entry: BlinkConfigEntry) -> bool:
    """Unload Blink entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
