"""Support for LaMetric time."""

from menuai.components import notify as menuai_notify
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_NAME, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import LaMetricDataUpdateCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the LaMetric integration."""
    async_setup_services(menuai)
    menuai.data[DOMAIN] = {"menuai_config": config}
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up LaMetric from a config entry."""
    coordinator = LaMetricDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN][entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {CONF_NAME: coordinator.data.name, "entry_id": entry.entry_id},
            menuai.data[DOMAIN]["menuai_config"],
        )
    )
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload LaMetric config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        del menuai.data[DOMAIN][entry.entry_id]
        await menuai_notify.async_reload(menuai, DOMAIN)
    return unload_ok
