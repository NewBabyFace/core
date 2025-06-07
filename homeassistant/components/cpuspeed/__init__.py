"""The CPU Speed integration."""

from cpuinfo import cpuinfo

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import LOGGER, PLATFORMS


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    if not await menuai.async_add_executor_job(cpuinfo.get_cpu_info):
        LOGGER.error(
            "Unable to get CPU information, the CPU Speed integration "
            "is not compatible with your system"
        )
        return False

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
