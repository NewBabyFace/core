"""The Israel Rail component."""

import logging

from israelrailapi import TrainSchedule

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import CONF_DESTINATION, CONF_START, DOMAIN
from .coordinator import IsraelRailConfigEntry, IsraelRailDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: IsraelRailConfigEntry) -> bool:
    """Set up Israel rail from a config entry."""
    config = entry.data

    start = config[CONF_START]
    destination = config[CONF_DESTINATION]

    train_schedule = TrainSchedule()

    try:
        await menuai.async_add_executor_job(train_schedule.query, start, destination)
    except Exception as e:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="request_timeout",
            translation_placeholders={
                "config_title": entry.title,
                "error": str(e),
            },
        ) from e

    israel_rail_coordinator = IsraelRailDataUpdateCoordinator(
        menuai, entry, train_schedule, start, destination
    )
    await israel_rail_coordinator.async_config_entry_first_refresh()
    entry.runtime_data = israel_rail_coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: IsraelRailConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
