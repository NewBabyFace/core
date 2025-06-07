"""The Obihai integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.helpers.device_registry import format_mac

from .connectivity import ObihaiConnection
from .const import DOMAIN, LOGGER, PLATFORMS


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    requester = ObihaiConnection(
        entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )
    await menuai.async_add_executor_job(requester.update)
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = requester
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_migrate_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    version = entry.version

    LOGGER.debug("Migrating from version %s", version)
    if version != 2:
        requester: ObihaiConnection = menuai.data[DOMAIN][entry.entry_id]

        device_mac = await menuai.async_add_executor_job(
            requester.pyobihai.get_device_mac
        )
        menuai.config_entries.async_update_entry(
            entry, unique_id=format_mac(device_mac), version=2
        )

    LOGGER.debug("Migration to version %s successful", entry.version)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
