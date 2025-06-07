"""Support for HomematicIP Cloud devices."""

import voluptuous as vol

from menuai import config_entries
from menuai.const import CONF_NAME, EVENT_menuai_STOP
from menuai.core import menuai, callback
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from menuai.helpers.typing import ConfigType

from .const import (
    CONF_ACCESSPOINT,
    CONF_AUTHTOKEN,
    DOMAIN,
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
)
from .hap import HomematicIPConfigEntry, HomematicipHAP
from .services import async_setup_services

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Optional(CONF_NAME, default=""): vol.Any(cv.string),
                        vol.Required(CONF_ACCESSPOINT): cv.string,
                        vol.Required(CONF_AUTHTOKEN): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the HomematicIP Cloud component."""
    accesspoints = config.get(DOMAIN, [])

    for conf in accesspoints:
        if conf[CONF_ACCESSPOINT] not in {
            entry.data[HMIPC_HAPID]
            for entry in menuai.config_entries.async_entries(DOMAIN)
        }:
            menuai.async_create_task(
                menuai.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={
                        HMIPC_HAPID: conf[CONF_ACCESSPOINT],
                        HMIPC_AUTHTOKEN: conf[CONF_AUTHTOKEN],
                        HMIPC_NAME: conf[CONF_NAME],
                    },
                )
            )

    await async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: HomematicIPConfigEntry) -> bool:
    """Set up an access point from a config entry."""

    # 0.104 introduced config entry unique id, this makes upgrading possible
    if entry.unique_id is None:
        new_data = dict(entry.data)

        menuai.config_entries.async_update_entry(
            entry, unique_id=new_data[HMIPC_HAPID], data=new_data
        )

    hap = HomematicipHAP(menuai, entry)

    entry.runtime_data = hap
    if not await hap.async_setup():
        return False

    _async_remove_obsolete_entities(menuai, entry, hap)

    # Register on HA stop event to gracefully shutdown HomematicIP Cloud connection
    hap.reset_connection_listener = menuai.bus.async_listen_once(
        EVENT_menuai_STOP, hap.shutdown
    )

    # Register hap as device in registry.
    device_registry = dr.async_get(menuai)

    home = hap.home
    hapname = home.label if home.label != entry.unique_id else f"Home-{home.label}"

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, home.id)},
        manufacturer="eQ-3",
        # Add the name from config entry.
        name=hapname,
    )
    return True


async def async_unload_entry(
    menuai: menuai, entry: HomematicIPConfigEntry
) -> bool:
    """Unload a config entry."""
    hap = entry.runtime_data
    assert hap.reset_connection_listener is not None
    hap.reset_connection_listener()

    return await hap.async_reset()


@callback
def _async_remove_obsolete_entities(
    menuai: menuai, entry: HomematicIPConfigEntry, hap: HomematicipHAP
):
    """Remove obsolete entities from entity registry."""

    if hap.home.currentAPVersion < "2.2.12":
        return

    entity_registry = er.async_get(menuai)
    er_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    for er_entry in er_entries:
        if er_entry.unique_id.startswith("HomematicipAccesspointStatus"):
            entity_registry.async_remove(er_entry.entity_id)
            continue

        for hapid in hap.home.accessPointUpdateStates:
            if er_entry.unique_id == f"HomematicipBatterySensor_{hapid}":
                entity_registry.async_remove(er_entry.entity_id)
