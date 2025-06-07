"""The pushover component."""

from __future__ import annotations

from pushover_complete import BadAPIRequestError, PushoverAPI
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_NAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import CONF_USER_KEY, DATA_menuai_CONFIG, DOMAIN

PLATFORMS = [Platform.NOTIFY]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the pushover component."""

    menuai.data[DATA_menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up pushover from a config entry."""

    # remove unique_id for beta users
    if entry.unique_id is not None:
        menuai.config_entries.async_update_entry(entry, unique_id=None)

    pushover_api = PushoverAPI(entry.data[CONF_API_KEY])
    try:
        await menuai.async_add_executor_job(
            pushover_api.validate, entry.data[CONF_USER_KEY]
        )

    except (BadAPIRequestError, ValueError, RequestException, HTTPError) as err:
        if "application token is invalid" in str(err):
            raise ConfigEntryAuthFailed(err) from err
        raise ConfigEntryNotReady(err) from err

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = pushover_api

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: entry.data[CONF_NAME],
                CONF_USER_KEY: entry.data[CONF_USER_KEY],
                "entry_id": entry.entry_id,
            },
            menuai.data[DATA_menuai_CONFIG],
        )
    )

    return True
