"""The SRP Energy integration."""

from srpenergy.client import SrpEnergyClient

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai

from .const import DOMAIN, LOGGER
from .coordinator import SRPEnergyDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the SRP Energy component from a config entry."""
    api_account_id: str = entry.data[CONF_ID]
    api_username: str = entry.data[CONF_USERNAME]
    api_password: str = entry.data[CONF_PASSWORD]

    LOGGER.debug("Configuring client using account_id %s", api_account_id)

    api_instance = SrpEnergyClient(
        api_account_id,
        api_username,
        api_password,
    )

    coordinator = SRPEnergyDataUpdateCoordinator(menuai, entry, api_instance)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
