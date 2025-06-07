"""The seventeentrack component."""

from pyseventeentrack import Client as SeventeenTrackClient
from pyseventeentrack.errors import SeventeenTrackError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import SeventeenTrackCoordinator
from .services import setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the 17Track component."""

    setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up 17Track from a config entry."""

    session = async_get_clientsession(menuai)
    client = SeventeenTrackClient(session=session)

    try:
        await client.profile.login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    except SeventeenTrackError as err:
        raise ConfigEntryNotReady from err

    seventeen_coordinator = SeventeenTrackCoordinator(menuai, entry, client)

    await seventeen_coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = seventeen_coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
