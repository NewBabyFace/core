"""The tests for Alarm control panel platforms."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai


async def help_async_setup_entry_init(
    menuai: menuai, config_entry: ConfigEntry
) -> bool:
    """Set up test config entry."""
    await menuai.config_entries.async_forward_entry_setups(
        config_entry, [Platform.ALARM_CONTROL_PANEL]
    )
    return True


async def help_async_unload_entry(
    menuai: menuai, config_entry: ConfigEntry
) -> bool:
    """Unload test config emntry."""
    return await menuai.config_entries.async_unload_platforms(
        config_entry, [Platform.ALARM_CONTROL_PANEL]
    )
