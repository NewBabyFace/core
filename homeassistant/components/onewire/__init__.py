"""The 1-Wire component."""

import logging

from pyownet import protocol

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .const import DOMAIN
from .onewirehub import OneWireConfigEntry, OneWireHub

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: OneWireConfigEntry) -> bool:
    """Set up a 1-Wire proxy for a config entry."""
    onewire_hub = OneWireHub(menuai, entry)
    try:
        await onewire_hub.initialize()
    except (
        protocol.ConnError,  # Failed to connect to the server
        protocol.OwnetError,  # Connected to server, but failed to list the devices
    ) as exc:
        raise ConfigEntryNotReady from exc

    entry.runtime_data = onewire_hub

    await menuai.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    onewire_hub.schedule_scan_for_new_devices()

    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: OneWireConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    onewire_hub = config_entry.runtime_data
    return not device_entry.identifiers.intersection(
        (DOMAIN, device.id) for device in onewire_hub.devices or []
    )


async def async_unload_entry(
    menuai: menuai, config_entry: OneWireConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, _PLATFORMS)


async def options_update_listener(
    menuai: menuai, entry: OneWireConfigEntry
) -> None:
    """Handle options update."""
    _LOGGER.debug("Configuration options updated, reloading OneWire integration")
    await menuai.config_entries.async_reload(entry.entry_id)
