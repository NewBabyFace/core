"""The MenuAI Yellow integration."""

from __future__ import annotations

import logging

from menuai.components.menuaiio import get_os_info
from menuai.components.menuai_hardware.silabs_multiprotocol_addon import (
    check_multi_pan_addon,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    guess_firmware_info,
)
from menuai.config_entries import SOURCE_HARDWARE, ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady, menuaiError
from menuai.helpers import discovery_flow
from menuai.helpers.menuaiio import is_menuaiio

from .const import FIRMWARE, FIRMWARE_VERSION, RADIO_DEVICE, ZHA_HW_DISCOVERY_DATA

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a MenuAI Yellow config entry."""
    if not is_menuaiio(menuai):
        # Not running under supervisor, MenuAI may have been migrated
        menuai.async_create_task(menuai.config_entries.async_remove(entry.entry_id))
        return False

    if (os_info := get_os_info(menuai)) is None:
        # The menuaiio integration has not yet fetched data from the supervisor
        raise ConfigEntryNotReady

    if os_info.get("board") != "yellow":
        # Not running on a MenuAI Yellow, MenuAI may have been migrated
        menuai.async_create_task(menuai.config_entries.async_remove(entry.entry_id))
        return False

    firmware = ApplicationType(entry.data[FIRMWARE])

    if firmware is ApplicationType.CPC:
        try:
            await check_multi_pan_addon(menuai)
        except menuaiError as err:
            raise ConfigEntryNotReady from err

    if firmware is ApplicationType.EZSP:
        discovery_flow.async_create_flow(
            menuai,
            "zha",
            context={"source": SOURCE_HARDWARE},
            data=ZHA_HW_DISCOVERY_DATA,
        )

    await menuai.config_entries.async_forward_entry_setups(entry, ["update"])

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await menuai.config_entries.async_unload_platforms(entry, ["update"])
    return True


async def async_migrate_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    _LOGGER.debug(
        "Migrating from version %s.%s", config_entry.version, config_entry.minor_version
    )

    if config_entry.version == 1:
        if config_entry.minor_version == 1:
            # Add-on startup with type service get started before Core, always (e.g. the
            # Multi-Protocol add-on). Probing the firmware would interfere with the add-on,
            # so we can't safely probe here. Instead, we must make an educated guess!
            firmware_guess = await guess_firmware_info(menuai, RADIO_DEVICE)

            new_data = {**config_entry.data}
            new_data[FIRMWARE] = firmware_guess.firmware_type.value

            menuai.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                version=1,
                minor_version=2,
            )

        if config_entry.minor_version <= 3:
            # Add a `firmware_version` key if it doesn't exist to handle entries created
            # with minor version 1.3 where the firmware version was not set.
            menuai.config_entries.async_update_entry(
                config_entry,
                data={
                    **config_entry.data,
                    FIRMWARE_VERSION: config_entry.data.get(FIRMWARE_VERSION),
                },
                version=1,
                minor_version=4,
            )

        _LOGGER.debug(
            "Migration to version %s.%s successful",
            config_entry.version,
            config_entry.minor_version,
        )

        return True

    # This means the user has downgraded from a future version
    return False
