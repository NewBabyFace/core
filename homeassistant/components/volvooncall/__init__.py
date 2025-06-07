"""Support for Volvo On Call."""

from volvooncall import Connection

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_UNIT_SYSTEM,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCANDINAVIAN_MILES,
    DOMAIN,
    PLATFORMS,
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_SCANDINAVIAN_MILES,
)
from .coordinator import VolvoUpdateCoordinator
from .models import VolvoData


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the Volvo On Call component from a ConfigEntry."""

    # added CONF_UNIT_SYSTEM / deprecated CONF_SCANDINAVIAN_MILES in 2022.10 to support imperial units
    if CONF_UNIT_SYSTEM not in entry.data:
        new_conf = {**entry.data}

        scandinavian_miles: bool = entry.data[CONF_SCANDINAVIAN_MILES]

        new_conf[CONF_UNIT_SYSTEM] = (
            UNIT_SYSTEM_SCANDINAVIAN_MILES if scandinavian_miles else UNIT_SYSTEM_METRIC
        )

        menuai.config_entries.async_update_entry(entry, data=new_conf)

    session = async_get_clientsession(menuai)

    connection = Connection(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        service_url=None,
        region=entry.data[CONF_REGION],
    )

    menuai.data.setdefault(DOMAIN, {})

    volvo_data = VolvoData(menuai, connection, entry)

    coordinator = VolvoUpdateCoordinator(menuai, entry, volvo_data)

    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
