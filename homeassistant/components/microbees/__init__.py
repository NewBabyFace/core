"""The microBees integration."""

from dataclasses import dataclass
from http import HTTPStatus

import aiohttp
from microBeesPy import MicroBees

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_entry_oauth2_flow

from .const import DOMAIN, PLATFORMS
from .coordinator import MicroBeesUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class menuaiMicroBeesData:
    """Microbees data stored in the MenuAI data object."""

    connector: MicroBees
    coordinator: MicroBeesUpdateCoordinator
    session: config_entry_oauth2_flow.OAuth2Session


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up microBees from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as ex:
        if ex.status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        ):
            raise ConfigEntryAuthFailed("Token not valid, trigger renewal") from ex
        raise ConfigEntryNotReady from ex
    microbees = MicroBees(token=session.token[CONF_ACCESS_TOKEN])
    coordinator = MicroBeesUpdateCoordinator(menuai, entry, microbees)
    await coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = menuaiMicroBeesData(
        connector=microbees,
        coordinator=coordinator,
        session=session,
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
