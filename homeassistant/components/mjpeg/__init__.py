"""The MJPEG IP Camera integration."""

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .camera import MjpegCamera
from .const import CONF_MJPEG_URL, CONF_STILL_IMAGE_URL, DOMAIN, PLATFORMS
from .util import filter_urllib3_logging

__all__ = [
    "CONF_MJPEG_URL",
    "CONF_STILL_IMAGE_URL",
    "MjpegCamera",
    "filter_urllib3_logging",
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the MJPEG IP Camera integration."""
    filter_urllib3_logging()
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entry when its updated.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await menuai.config_entries.async_reload(entry.entry_id)
