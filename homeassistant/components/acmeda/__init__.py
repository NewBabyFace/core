"""The Rollease Acmeda Automate integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .hub import PulseHub

CONF_HUBS = "hubs"

PLATFORMS = [Platform.COVER, Platform.SENSOR]

type AcmedaConfigEntry = ConfigEntry[PulseHub]


async def async_setup_entry(
    menuai: menuai, config_entry: AcmedaConfigEntry
) -> bool:
    """Set up Rollease Acmeda Automate hub from a config entry."""

    await _migrate_unique_ids(menuai, config_entry)

    hub = PulseHub(menuai, config_entry)

    if not await hub.async_setup():
        return False

    config_entry.runtime_data = hub
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def _migrate_unique_ids(menuai: menuai, entry: AcmedaConfigEntry) -> None:
    """Migrate pre-config flow unique ids."""
    entity_registry = er.async_get(menuai)
    registry_entries = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )
    for reg_entry in registry_entries:
        if isinstance(reg_entry.unique_id, int):  # type: ignore[unreachable]
            entity_registry.async_update_entity(  # type: ignore[unreachable]
                reg_entry.entity_id, new_unique_id=str(reg_entry.unique_id)
            )


async def async_unload_entry(
    menuai: menuai, config_entry: AcmedaConfigEntry
) -> bool:
    """Unload a config entry."""
    hub = config_entry.runtime_data

    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if not await hub.async_reset():
        return False

    return unload_ok
