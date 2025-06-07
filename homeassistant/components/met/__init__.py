"""The met component."""

from __future__ import annotations

import logging

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import (
    CONF_TRACK_HOME,
    DEFAULT_HOME_LATITUDE,
    DEFAULT_HOME_LONGITUDE,
    DOMAIN,
)
from .coordinator import MetDataUpdateCoordinator, MetWeatherConfigEntry

PLATFORMS = [Platform.WEATHER]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    menuai: menuai, config_entry: MetWeatherConfigEntry
) -> bool:
    """Set up Met as config entry."""
    # Don't setup if tracking home location and latitude or longitude isn't set.
    # Also, filters out our onboarding default location.
    if config_entry.data.get(CONF_TRACK_HOME, False) and (
        (not menuai.config.latitude and not menuai.config.longitude)
        or (
            menuai.config.latitude == DEFAULT_HOME_LATITUDE
            and menuai.config.longitude == DEFAULT_HOME_LONGITUDE
        )
    ):
        _LOGGER.warning(
            "Skip setting up met.no integration; No Home location has been set"
        )
        return False

    coordinator = MetDataUpdateCoordinator(menuai, config_entry)
    await coordinator.async_config_entry_first_refresh()

    if config_entry.data.get(CONF_TRACK_HOME, False):
        coordinator.track_home()

    config_entry.runtime_data = coordinator

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    config_entry.async_on_unload(coordinator.untrack_home)

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await cleanup_old_device(menuai)

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: MetWeatherConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_update_entry(menuai: menuai, config_entry: MetWeatherConfigEntry):
    """Reload Met component when options changed."""
    await menuai.config_entries.async_reload(config_entry.entry_id)


async def cleanup_old_device(menuai: menuai) -> None:
    """Cleanup device without proper device identifier."""
    device_reg = dr.async_get(menuai)
    device = device_reg.async_get_device(identifiers={(DOMAIN,)})  # type: ignore[arg-type]
    if device:
        _LOGGER.debug("Removing improper device %s", device.name)
        device_reg.async_remove_device(device.id)
