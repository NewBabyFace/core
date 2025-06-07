"""The jvc_projector integration."""

from __future__ import annotations

from jvcprojector import JvcProjector, JvcProjectorAuthError, JvcProjectorConnectError

from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .coordinator import JVCConfigEntry, JvcProjectorDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.REMOTE, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: JVCConfigEntry) -> bool:
    """Set up integration from a config entry."""
    device = JvcProjector(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        await device.connect(True)
    except JvcProjectorConnectError as err:
        await device.disconnect()
        raise ConfigEntryNotReady(
            f"Unable to connect to {entry.data[CONF_HOST]}"
        ) from err
    except JvcProjectorAuthError as err:
        await device.disconnect()
        raise ConfigEntryAuthFailed("Password authentication failed") from err

    coordinator = JvcProjectorDataUpdateCoordinator(menuai, entry, device)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    async def disconnect(event: Event) -> None:
        await device.disconnect()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, disconnect)
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: JVCConfigEntry) -> bool:
    """Unload config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.device.disconnect()
    return unload_ok
