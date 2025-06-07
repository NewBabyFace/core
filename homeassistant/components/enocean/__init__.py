"""Support for EnOcean devices."""

import voluptuous as vol

from menuai.config_entries import SOURCE_IMPORT, ConfigEntry
from menuai.const import CONF_DEVICE
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DATA_ENOCEAN, DOMAIN, ENOCEAN_DONGLE
from .dongle import EnOceanDongle

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_DEVICE): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the EnOcean component."""
    # support for text-based configuration (legacy)
    if DOMAIN not in config:
        return True

    if menuai.config_entries.async_entries(DOMAIN):
        # We can only have one dongle. If there is already one in the config,
        # there is no need to import the yaml based config.
        return True

    menuai.async_create_task(
        menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
        )
    )

    return True


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Set up an EnOcean dongle for the given entry."""
    enocean_data = menuai.data.setdefault(DATA_ENOCEAN, {})
    usb_dongle = EnOceanDongle(menuai, config_entry.data[CONF_DEVICE])
    await usb_dongle.async_setup()
    enocean_data[ENOCEAN_DONGLE] = usb_dongle

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload EnOcean config entry."""

    enocean_dongle = menuai.data[DATA_ENOCEAN][ENOCEAN_DONGLE]
    enocean_dongle.unload()
    menuai.data.pop(DATA_ENOCEAN)

    return True
