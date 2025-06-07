"""The P1 Monitor integration."""

from __future__ import annotations

from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import LOGGER
from .coordinator import P1MonitorConfigEntry, P1MonitorDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: P1MonitorConfigEntry) -> bool:
    """Set up P1 Monitor from a config entry."""

    coordinator = P1MonitorDataUpdateCoordinator(menuai, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.p1monitor.close()
        raise

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(
    menuai: menuai, config_entry: P1MonitorConfigEntry
) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migrate to split host and port
        host = config_entry.data[CONF_HOST]
        if ":" in host:
            host, port = host.split(":")
        else:
            port = 80

        new_data = {
            **config_entry.data,
            CONF_HOST: host,
            CONF_PORT: int(port),
        }

        menuai.config_entries.async_update_entry(config_entry, data=new_data, version=2)
        LOGGER.debug("Migration to version %s successful", config_entry.version)
    return True


async def async_unload_entry(menuai: menuai, entry: P1MonitorConfigEntry) -> bool:
    """Unload P1 Monitor config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
