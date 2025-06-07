"""Support for EQ3 devices."""

import asyncio
import logging
from typing import TYPE_CHECKING

from eq3btsmart import Thermostat
from eq3btsmart.exceptions import Eq3Exception
from eq3btsmart.thermostat_config import ThermostatConfig

from menuai.components import bluetooth
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_THERMOSTAT_CONNECTED, SIGNAL_THERMOSTAT_DISCONNECTED
from .models import Eq3Config, Eq3ConfigEntryData

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


type Eq3ConfigEntry = ConfigEntry[Eq3ConfigEntryData]


async def async_setup_entry(menuai: menuai, entry: Eq3ConfigEntry) -> bool:
    """Handle config entry setup."""

    mac_address: str | None = entry.unique_id

    if TYPE_CHECKING:
        assert mac_address is not None

    eq3_config = Eq3Config(
        mac_address=mac_address,
    )

    device = bluetooth.async_ble_device_from_address(
        menuai, mac_address.upper(), connectable=True
    )

    if device is None:
        raise ConfigEntryNotReady(
            f"[{eq3_config.mac_address}] Device could not be found"
        )

    thermostat = Thermostat(
        thermostat_config=ThermostatConfig(
            mac_address=mac_address,
        ),
        ble_device=device,
    )

    entry.runtime_data = Eq3ConfigEntryData(
        eq3_config=eq3_config, thermostat=thermostat
    )
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        menuai, _async_run_thermostat(menuai, entry), entry.entry_id
    )

    return True


async def async_unload_entry(menuai: menuai, entry: Eq3ConfigEntry) -> bool:
    """Handle config entry unload."""

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.thermostat.async_disconnect()

    return unload_ok


async def update_listener(menuai: menuai, entry: Eq3ConfigEntry) -> None:
    """Handle config entry update."""

    await menuai.config_entries.async_reload(entry.entry_id)


async def _async_run_thermostat(menuai: menuai, entry: Eq3ConfigEntry) -> None:
    """Run the thermostat."""

    thermostat = entry.runtime_data.thermostat
    mac_address = entry.runtime_data.eq3_config.mac_address
    scan_interval = entry.runtime_data.eq3_config.scan_interval

    await _async_reconnect_thermostat(menuai, entry)

    while True:
        try:
            await thermostat.async_get_status()
        except Eq3Exception as e:
            if not thermostat.is_connected:
                _LOGGER.error(
                    "[%s] eQ-3 device disconnected",
                    mac_address,
                )
                async_dispatcher_send(
                    menuai,
                    f"{SIGNAL_THERMOSTAT_DISCONNECTED}_{mac_address}",
                )
                await _async_reconnect_thermostat(menuai, entry)
                continue

            _LOGGER.error(
                "[%s] Error updating eQ-3 device: %s",
                mac_address,
                e,
            )

        await asyncio.sleep(scan_interval)


async def _async_reconnect_thermostat(
    menuai: menuai, entry: Eq3ConfigEntry
) -> None:
    """Reconnect the thermostat."""

    thermostat = entry.runtime_data.thermostat
    mac_address = entry.runtime_data.eq3_config.mac_address
    scan_interval = entry.runtime_data.eq3_config.scan_interval

    while True:
        try:
            await thermostat.async_connect()
        except Eq3Exception:
            await asyncio.sleep(scan_interval)
            continue

        _LOGGER.debug(
            "[%s] eQ-3 device connected",
            mac_address,
        )

        async_dispatcher_send(
            menuai,
            f"{SIGNAL_THERMOSTAT_CONNECTED}_{mac_address}",
        )

        return
