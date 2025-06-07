"""The OurGroceries integration."""

from __future__ import annotations

from aiohttp import ClientError
from ourgroceries import OurGroceries
from ourgroceries.exceptions import InvalidLoginException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import OurGroceriesDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.TODO]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up OurGroceries from a config entry."""

    menuai.data.setdefault(DOMAIN, {})
    data = entry.data
    og = OurGroceries(data[CONF_USERNAME], data[CONF_PASSWORD])
    try:
        await og.login()
    except (TimeoutError, ClientError) as error:
        raise ConfigEntryNotReady from error
    except InvalidLoginException:
        return False

    coordinator = OurGroceriesDataUpdateCoordinator(menuai, entry, og)
    await coordinator.async_config_entry_first_refresh()
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
