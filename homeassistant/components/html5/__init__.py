"""The html5 component."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import discovery

from .const import DOMAIN


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up HTML5 from a config entry."""
    await discovery.async_load_platform(
        menuai, Platform.NOTIFY, DOMAIN, dict(entry.data), {}
    )
    return True
