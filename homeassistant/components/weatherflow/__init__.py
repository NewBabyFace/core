"""Get data from Smart Weather station via UDP."""

from __future__ import annotations

from pyweatherflowudp.client import EVENT_DEVICE_DISCOVERED, WeatherFlowListener
from pyweatherflowudp.device import EVENT_LOAD_COMPLETE, WeatherFlowDevice
from pyweatherflowudp.errors import ListenerError

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.device_registry import DeviceEntry
from menuai.helpers.dispatcher import async_dispatcher_send
from menuai.helpers.start import async_at_started

from .const import DOMAIN, LOGGER, format_dispatch_call

PLATFORMS = [
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up WeatherFlow from a config entry."""

    client = WeatherFlowListener()

    @callback
    def _async_device_discovered(device: WeatherFlowDevice) -> None:
        LOGGER.debug("Found a device: %s", device)

        @callback
        def _async_add_device_if_started(device: WeatherFlowDevice):
            async_at_started(
                menuai,
                callback(
                    lambda _: async_dispatcher_send(
                        menuai, format_dispatch_call(entry), device
                    )
                ),
            )

        entry.async_on_unload(
            device.on(
                EVENT_LOAD_COMPLETE,
                lambda _: _async_add_device_if_started(device),
            )
        )

    entry.async_on_unload(client.on(EVENT_DEVICE_DISCOVERED, _async_device_discovered))

    try:
        await client.start_listening()
    except ListenerError as ex:
        raise ConfigEntryNotReady from ex

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_handle_ha_shutdown(event: Event) -> None:
        """Handle HA shutdown."""
        await client.stop_listening()

    entry.async_on_unload(
        menuai.bus.async_listen(EVENT_menuai_STOP, _async_handle_ha_shutdown)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        client: WeatherFlowListener = menuai.data[DOMAIN].pop(entry.entry_id, None)
        if client:
            await client.stop_listening()

    return unload_ok


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    client: WeatherFlowListener = menuai.data[DOMAIN][config_entry.entry_id]
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for device in client.devices
        if device.serial_number == identifier[1]
    )
