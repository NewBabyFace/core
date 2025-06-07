"""The Mikrotik component."""

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .const import ATTR_MANUFACTURER, DOMAIN
from .coordinator import MikrotikConfigEntry, MikrotikDataUpdateCoordinator, get_api
from .errors import CannotConnect, LoginError

PLATFORMS = [Platform.DEVICE_TRACKER]


async def async_setup_entry(
    menuai: menuai, config_entry: MikrotikConfigEntry
) -> bool:
    """Set up the Mikrotik component."""
    try:
        api = await menuai.async_add_executor_job(get_api, dict(config_entry.data))
    except CannotConnect as api_error:
        raise ConfigEntryNotReady from api_error
    except LoginError as err:
        raise ConfigEntryAuthFailed from err

    coordinator = MikrotikDataUpdateCoordinator(menuai, config_entry, api)
    await menuai.async_add_executor_job(coordinator.api.get_hub_details)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(DOMAIN, coordinator.serial_num)},
        manufacturer=ATTR_MANUFACTURER,
        model=coordinator.model,
        name=coordinator.hostname,
        sw_version=coordinator.firmware,
    )

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: MikrotikConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)
