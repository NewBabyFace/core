"""The Dexcom integration."""

from pydexcom import AccountError, Dexcom, SessionError

from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import CONF_SERVER, PLATFORMS, SERVER_OUS
from .coordinator import DexcomConfigEntry, DexcomCoordinator


async def async_setup_entry(menuai: menuai, entry: DexcomConfigEntry) -> bool:
    """Set up Dexcom from a config entry."""
    try:
        dexcom = await menuai.async_add_executor_job(
            Dexcom,
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_SERVER] == SERVER_OUS,
        )
    except AccountError:
        return False
    except SessionError as error:
        raise ConfigEntryNotReady from error

    coordinator = DexcomCoordinator(menuai, entry=entry, dexcom=dexcom)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: DexcomConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
