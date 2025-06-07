"""The habitica integration."""

from habiticalib import Habitica

from menuai.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import CONF_API_USER, DOMAIN, X_CLIENT
from .coordinator import HabiticaConfigEntry, HabiticaDataUpdateCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.IMAGE,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TODO,
]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Habitica service."""

    async_setup_services(menuai)
    return True


async def async_setup_entry(
    menuai: menuai, config_entry: HabiticaConfigEntry
) -> bool:
    """Set up habitica from a config entry."""

    session = async_get_clientsession(
        menuai, verify_ssl=config_entry.data.get(CONF_VERIFY_SSL, True)
    )

    api = Habitica(
        session,
        api_user=config_entry.data[CONF_API_USER],
        api_key=config_entry.data[CONF_API_KEY],
        url=config_entry.data[CONF_URL],
        x_client=X_CLIENT,
    )

    coordinator = HabiticaDataUpdateCoordinator(menuai, config_entry, api)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: HabiticaConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
