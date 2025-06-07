"""Support the UPB PIM."""

import logging

import upb_lib

from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_COMMAND, CONF_FILE_PATH, CONF_HOST, Platform
from menuai.core import menuai

from .const import (
    ATTR_ADDRESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_RATE,
    DOMAIN,
    EVENT_UPB_SCENE_CHANGED,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.LIGHT, Platform.SCENE]


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Set up a new config_entry for UPB PIM."""

    url = config_entry.data[CONF_HOST]
    file = config_entry.data[CONF_FILE_PATH]

    upb = upb_lib.UpbPim({"url": url, "UPStartExportFile": file})
    await upb.load_upstart_file()
    await upb.async_connect()
    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][config_entry.entry_id] = {"upb": upb}

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    def _element_changed(element, changeset):
        if (change := changeset.get("last_change")) is None:
            return
        if change.get("command") is None:
            return

        menuai.bus.async_fire(
            EVENT_UPB_SCENE_CHANGED,
            {
                ATTR_COMMAND: change["command"],
                ATTR_ADDRESS: element.addr.index,
                ATTR_BRIGHTNESS_PCT: change.get("level", -1),
                ATTR_RATE: change.get("rate", -1),
            },
        )

    for link in upb.links:
        element = upb.links[link]
        element.add_callback(_element_changed)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload the config_entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        upb = menuai.data[DOMAIN][config_entry.entry_id]["upb"]
        upb.disconnect()
        menuai.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_migrate_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Migrate entry."""

    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        # 1 -> 2: Unique ID from integer to string
        if entry.minor_version == 1:
            minor_version = 2
            menuai.config_entries.async_update_entry(
                entry, unique_id=str(entry.unique_id), minor_version=minor_version
            )

    _LOGGER.debug("Migration successful")

    return True
