"""Helpers for cookidoo."""

from typing import Any

from cookidoo_api import Cookidoo, CookidooConfig, get_localization_options

from menuai.const import CONF_COUNTRY, CONF_EMAIL, CONF_LANGUAGE, CONF_PASSWORD
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import CookidooConfigEntry


async def cookidoo_from_config_data(
    menuai: menuai, data: dict[str, Any]
) -> Cookidoo:
    """Build cookidoo from config data."""
    localizations = await get_localization_options(
        country=data[CONF_COUNTRY].lower(),
        language=data[CONF_LANGUAGE],
    )

    return Cookidoo(
        async_get_clientsession(menuai),
        CookidooConfig(
            email=data[CONF_EMAIL],
            password=data[CONF_PASSWORD],
            localization=localizations[0],
        ),
    )


async def cookidoo_from_config_entry(
    menuai: menuai, entry: CookidooConfigEntry
) -> Cookidoo:
    """Build cookidoo from config entry."""
    return await cookidoo_from_config_data(menuai, dict(entry.data))
