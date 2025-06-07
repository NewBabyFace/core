"""The Fully Kiosk Browser integration."""

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import FullyKioskConfigEntry, FullyKioskDataUpdateCoordinator
from .services import async_setup_services

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.IMAGE,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Fully Kiosk Browser."""

    await async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: FullyKioskConfigEntry) -> bool:
    """Set up Fully Kiosk Browser from a config entry."""

    coordinator = FullyKioskDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_update_listeners()

    return True


async def async_unload_entry(menuai: menuai, entry: FullyKioskConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
