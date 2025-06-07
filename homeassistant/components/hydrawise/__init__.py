"""Support for Hydrawise cloud."""

from pydrawise import auth, hybrid

from menuai.const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed

from .const import APP_ID
from .coordinator import (
    HydrawiseConfigEntry,
    HydrawiseMainDataUpdateCoordinator,
    HydrawiseUpdateCoordinators,
    HydrawiseWaterUseDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]

_REQUIRED_AUTH_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_API_KEY)


async def async_setup_entry(
    menuai: menuai, config_entry: HydrawiseConfigEntry
) -> bool:
    """Set up Hydrawise from a config entry."""
    if any(k not in config_entry.data for k in _REQUIRED_AUTH_KEYS):
        # If we are missing any required authentication keys, trigger a reauth flow.
        raise ConfigEntryAuthFailed

    hydrawise = hybrid.HybridClient(
        auth.HybridAuth(
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
            config_entry.data[CONF_API_KEY],
        ),
        app_id=APP_ID,
    )

    main_coordinator = HydrawiseMainDataUpdateCoordinator(menuai, config_entry, hydrawise)
    await main_coordinator.async_config_entry_first_refresh()
    water_use_coordinator = HydrawiseWaterUseDataUpdateCoordinator(
        menuai, config_entry, hydrawise, main_coordinator
    )
    await water_use_coordinator.async_config_entry_first_refresh()
    config_entry.runtime_data = HydrawiseUpdateCoordinators(
        main=main_coordinator,
        water_use=water_use_coordinator,
    )
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: HydrawiseConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
