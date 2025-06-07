"""The Kostal Plenticore Solar Inverter integration."""

import logging

from pykoplenti import ApiException

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import Plenticore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Kostal Plenticore Solar Inverter from a config entry."""
    menuai.data.setdefault(DOMAIN, {})

    plenticore = Plenticore(menuai, entry)

    if not await plenticore.async_setup():
        return False

    menuai.data[DOMAIN][entry.entry_id] = plenticore

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # remove API object
        plenticore = menuai.data[DOMAIN].pop(entry.entry_id)
        try:
            await plenticore.async_unload()
        except ApiException as err:
            _LOGGER.error("Error logging out from inverter: %s", err)

    return unload_ok
