"""The IKEA Idasen Desk integration."""

from __future__ import annotations

import logging

from bleak.exc import BleakError
from idasen_ha.errors import AuthFailedError

from menuai.components import bluetooth
from menuai.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from menuai.const import CONF_ADDRESS, EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai, callback
from menuai.exceptions import ConfigEntryNotReady

from .coordinator import IdasenDeskConfigEntry, IdasenDeskCoordinator

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.COVER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: IdasenDeskConfigEntry) -> bool:
    """Set up IKEA Idasen from a config entry."""
    address: str = entry.data[CONF_ADDRESS].upper()

    coordinator = IdasenDeskCoordinator(menuai, entry, address)
    entry.runtime_data = coordinator

    try:
        if not await coordinator.async_connect():
            raise ConfigEntryNotReady(f"Unable to connect to desk {address}")  # noqa: TRY301
    except (AuthFailedError, TimeoutError, BleakError, Exception) as ex:
        raise ConfigEntryNotReady(f"Unable to connect to desk {address}") from ex

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    @callback
    def _async_bluetooth_callback(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Update from a Bluetooth callback to ensure that a new BLEDevice is fetched."""
        _LOGGER.debug("Bluetooth callback triggered")
        menuai.async_create_task(coordinator.async_connect_if_expected())

    entry.async_on_unload(
        bluetooth.async_register_callback(
            menuai,
            _async_bluetooth_callback,
            BluetoothCallbackMatcher({ADDRESS: address}),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    async def _async_stop(event: Event) -> None:
        """Close the connection."""
        await coordinator.async_disconnect()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, _async_stop)
    )
    return True


async def _async_update_listener(
    menuai: menuai, entry: IdasenDeskConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: IdasenDeskConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = entry.runtime_data
        await coordinator.async_disconnect()
        bluetooth.async_rediscover_address(menuai, coordinator.address)

    return unload_ok
