"""The google_travel_time component."""

import logging

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.util import dt as dt_util

from .const import CONF_TIME

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Google Maps Travel Time from a config entry."""
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""

    if config_entry.version == 1:
        _LOGGER.debug(
            "Migrating from version %s.%s",
            config_entry.version,
            config_entry.minor_version,
        )
        options = dict(config_entry.options)
        if options.get(CONF_TIME) == "now":
            options[CONF_TIME] = None
        elif options.get(CONF_TIME) is not None:
            if dt_util.parse_time(options[CONF_TIME]) is None:
                try:
                    from_timestamp = dt_util.utc_from_timestamp(int(options[CONF_TIME]))
                    options[CONF_TIME] = (
                        f"{from_timestamp.time().hour:02}:{from_timestamp.time().minute:02}"
                    )
                except ValueError:
                    _LOGGER.error(
                        "Invalid time format found while migrating: %s. The old config never worked. Reset to default (empty)",
                        options[CONF_TIME],
                    )
                    options[CONF_TIME] = None
        menuai.config_entries.async_update_entry(config_entry, options=options, version=2)
        _LOGGER.debug(
            "Migration to version %s.%s successful",
            config_entry.version,
            config_entry.minor_version,
        )
    return True
