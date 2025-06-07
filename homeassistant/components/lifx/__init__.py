"""Support for LIFX."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import datetime, timedelta
import socket
from typing import Any

from aiolifx.aiolifx import Light
from aiolifx.connection import LIFXConnection
import voluptuous as vol

from menuai.components.light import DOMAIN as LIGHT_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_HOST,
    CONF_PORT,
    EVENT_menuai_STARTED,
    Platform,
)
from menuai.core import CALLBACK_TYPE, menuaiJob, menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.event import async_call_later, async_track_time_interval
from menuai.helpers.typing import ConfigType

from .const import _LOGGER, DATA_LIFX_MANAGER, DOMAIN, TARGET_ANY
from .coordinator import LIFXUpdateCoordinator
from .discovery import async_discover_devices, async_trigger_discovery
from .manager import LIFXManager
from .migration import async_migrate_entities_devices, async_migrate_legacy_entries
from .util import async_entry_is_legacy, async_get_legacy_entry, formatted_serial

CONF_SERVER = "server"
CONF_BROADCAST = "broadcast"


INTERFACE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SERVER): cv.string,
        vol.Optional(CONF_PORT): cv.port,
        vol.Optional(CONF_BROADCAST): cv.string,
    }
)

CONFIG_SCHEMA = vol.All(
    cv.deprecated(DOMAIN),
    vol.Schema(
        {
            DOMAIN: {
                LIGHT_DOMAIN: vol.Schema(vol.All(cv.ensure_list, [INTERFACE_SCHEMA]))
            }
        },
        extra=vol.ALLOW_EXTRA,
    ),
)


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
]
DISCOVERY_INTERVAL = timedelta(minutes=15)
MIGRATION_INTERVAL = timedelta(minutes=5)

DISCOVERY_COOLDOWN = 5


async def async_legacy_migration(
    menuai: menuai,
    legacy_entry: ConfigEntry,
    discovered_devices: Iterable[Light],
) -> bool:
    """Migrate config entries."""
    existing_serials = {
        entry.unique_id
        for entry in menuai.config_entries.async_entries(DOMAIN)
        if entry.unique_id and not async_entry_is_legacy(entry)
    }
    # device.mac_addr is not the mac_address, its the serial number
    hosts_by_serial = {device.mac_addr: device.ip_addr for device in discovered_devices}
    missing_discovery_count = async_migrate_legacy_entries(
        menuai, hosts_by_serial, existing_serials, legacy_entry
    )
    if missing_discovery_count:
        _LOGGER.debug(
            "Migration in progress, waiting to discover %s device(s)",
            missing_discovery_count,
        )
        return False

    _LOGGER.debug(
        "Migration successful, removing legacy entry %s", legacy_entry.entry_id
    )
    await menuai.config_entries.async_remove(legacy_entry.entry_id)
    return True


class LIFXDiscoveryManager:
    """Manage discovery and migration."""

    def __init__(self, menuai: menuai, migrating: bool) -> None:
        """Init the manager."""
        self.menuai = menuai
        self.lock = asyncio.Lock()
        self.migrating = migrating
        self._cancel_discovery: CALLBACK_TYPE | None = None

    @callback
    def async_setup_discovery_interval(self) -> None:
        """Set up discovery at an interval."""
        if self._cancel_discovery:
            self._cancel_discovery()
            self._cancel_discovery = None
        discovery_interval = (
            MIGRATION_INTERVAL if self.migrating else DISCOVERY_INTERVAL
        )
        _LOGGER.debug(
            "LIFX starting discovery with interval: %s and migrating: %s",
            discovery_interval,
            self.migrating,
        )
        self._cancel_discovery = async_track_time_interval(
            self.menuai, self.async_discovery, discovery_interval, cancel_on_shutdown=True
        )

    async def async_discovery(self, *_: Any) -> None:
        """Discovery and migrate LIFX devics."""
        migrating_was_in_progress = self.migrating

        async with self.lock:
            discovered = await async_discover_devices(self.menuai)

            if legacy_entry := async_get_legacy_entry(self.menuai):
                migration_complete = await async_legacy_migration(
                    self.menuai, legacy_entry, discovered
                )
                if migration_complete and migrating_was_in_progress:
                    self.migrating = False
                    _LOGGER.debug(
                        (
                            "LIFX migration complete, switching to normal discovery"
                            " interval: %s"
                        ),
                        DISCOVERY_INTERVAL,
                    )
                    self.async_setup_discovery_interval()

            if discovered:
                async_trigger_discovery(self.menuai, discovered)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the LIFX component."""
    menuai.data[DOMAIN] = {}
    migrating = bool(async_get_legacy_entry(menuai))
    discovery_manager = LIFXDiscoveryManager(menuai, migrating)

    @callback
    def _async_delayed_discovery(now: datetime) -> None:
        """Start an untracked task to discover devices.

        We do not want the discovery task to block startup.
        """
        menuai.async_create_background_task(
            discovery_manager.async_discovery(), "lifx-discovery"
        )

    # Let the system settle a bit before starting discovery
    # to reduce the risk we miss devices because the event
    # loop is blocked at startup.
    discovery_manager.async_setup_discovery_interval()
    async_call_later(
        menuai,
        DISCOVERY_COOLDOWN,
        menuaiJob(_async_delayed_discovery, cancel_on_shutdown=True),
    )
    menuai.bus.async_listen_once(
        EVENT_menuai_STARTED, discovery_manager.async_discovery
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up LIFX from a config entry."""
    if async_entry_is_legacy(entry):
        return True

    if legacy_entry := async_get_legacy_entry(menuai):
        # If the legacy entry still exists, harvest the entities
        # that are moving to this config entry.
        async_migrate_entities_devices(menuai, legacy_entry.entry_id, entry)

    assert entry.unique_id is not None
    domain_data = menuai.data[DOMAIN]
    if DATA_LIFX_MANAGER not in domain_data:
        manager = LIFXManager(menuai)
        domain_data[DATA_LIFX_MANAGER] = manager
        manager.async_setup()

    host = entry.data[CONF_HOST]
    connection = LIFXConnection(host, TARGET_ANY)
    try:
        await connection.async_setup()
    except socket.gaierror as ex:
        connection.async_stop()
        raise ConfigEntryNotReady(f"Could not resolve {host}: {ex}") from ex
    coordinator = LIFXUpdateCoordinator(menuai, entry, connection)
    coordinator.async_setup()
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        connection.async_stop()
        raise

    serial = formatted_serial(coordinator.serial_number)
    if serial != entry.unique_id:
        # If the serial number of the device does not match the unique_id
        # of the config entry, it likely means the DHCP lease has expired
        # and the device has been assigned a new IP address. We need to
        # wait for the next discovery to find the device at its new address
        # and update the config entry so we do not mix up devices.
        raise ConfigEntryNotReady(
            f"Unexpected device found at {host}; expected {entry.unique_id}, found {serial}"
        )
    domain_data[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if async_entry_is_legacy(entry):
        return True
    domain_data = menuai.data[DOMAIN]
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: LIFXUpdateCoordinator = domain_data.pop(entry.entry_id)
        coordinator.connection.async_stop()
    # Only the DATA_LIFX_MANAGER left, remove it.
    if len(domain_data) == 1:
        manager: LIFXManager = domain_data.pop(DATA_LIFX_MANAGER)
        manager.async_unload()
    return unload_ok
