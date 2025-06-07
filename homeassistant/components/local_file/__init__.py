"""The local_file component."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_FILE_PATH, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryError

from .const import DOMAIN
from .util import check_file_path_access

PLATFORMS = [Platform.CAMERA]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Local file from a config entry."""
    file_path: str = entry.options[CONF_FILE_PATH]
    if not await menuai.async_add_executor_job(check_file_path_access, file_path):
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="not_readable_path",
            translation_placeholders={"file_path": file_path},
        )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload Local file config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
