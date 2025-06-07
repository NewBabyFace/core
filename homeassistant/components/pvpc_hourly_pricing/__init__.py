"""The pvpc_hourly_pricing integration to collect Spain official electric prices."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_TOKEN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import ATTR_POWER, ATTR_POWER_P3, DOMAIN
from .coordinator import ElecPricesDataUpdateCoordinator
from .helpers import get_enabled_sensor_keys

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up pvpc hourly pricing from a config entry."""
    entity_registry = er.async_get(menuai)
    sensor_keys = get_enabled_sensor_keys(
        using_private_api=entry.data.get(CONF_API_TOKEN) is not None,
        entries=er.async_entries_for_config_entry(entity_registry, entry.entry_id),
    )
    coordinator = ElecPricesDataUpdateCoordinator(menuai, entry, sensor_keys)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    if any(
        entry.data.get(attrib) != entry.options.get(attrib)
        for attrib in (ATTR_POWER, ATTR_POWER_P3, CONF_API_TOKEN)
    ):
        # update entry replacing data with new options
        menuai.config_entries.async_update_entry(
            entry, data={**entry.data, **entry.options}
        )
        await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
