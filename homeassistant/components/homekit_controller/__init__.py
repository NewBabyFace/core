"""Support for Homekit device discovery."""

from __future__ import annotations

import asyncio
import contextlib
import logging

import aiohomekit
from aiohomekit.const import (
    BLE_TRANSPORT_SUPPORTED,
    COAP_TRANSPORT_SUPPORTED,
    IP_TRANSPORT_SUPPORTED,
)
from aiohomekit.exceptions import (
    AccessoryDisconnectedError,
    AccessoryNotFoundError,
    EncryptionError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_IDENTIFIERS, EVENT_menuai_STOP
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv, device_registry as dr
from menuai.helpers.typing import ConfigType
from menuai.util.async_ import create_eager_task

from .config_flow import normalize_hkid
from .connection import HKDevice
from .const import DOMAIN, KNOWN_DEVICES
from .utils import async_get_controller

# Ensure all the controllers get imported in the executor
# since they are loaded late.
if BLE_TRANSPORT_SUPPORTED:
    from aiohomekit.controller import ble  # noqa: F401
if COAP_TRANSPORT_SUPPORTED:
    from aiohomekit.controller import coap  # noqa: F401
if IP_TRANSPORT_SUPPORTED:
    from aiohomekit.controller import ip  # noqa: F401

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a HomeKit connection on a config entry."""
    conn = HKDevice(menuai, entry, entry.data)
    menuai.data[KNOWN_DEVICES][conn.unique_id] = conn

    # For backwards compat
    if entry.unique_id is None:
        menuai.config_entries.async_update_entry(
            entry, unique_id=normalize_hkid(conn.unique_id)
        )

    try:
        await conn.async_setup()
    except (
        TimeoutError,
        AccessoryNotFoundError,
        EncryptionError,
        AccessoryDisconnectedError,
    ) as ex:
        del menuai.data[KNOWN_DEVICES][conn.unique_id]
        with contextlib.suppress(TimeoutError):
            await conn.pairing.close()
        raise ConfigEntryNotReady from ex

    return True


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up for Homekit devices."""
    await async_get_controller(menuai)

    menuai.data[KNOWN_DEVICES] = {}

    async def _async_stop_homekit_controller(event: Event) -> None:
        await asyncio.gather(
            *(
                create_eager_task(connection.async_unload())
                for connection in menuai.data[KNOWN_DEVICES].values()
            )
        )

    menuai.bus.async_listen_once(EVENT_menuai_STOP, _async_stop_homekit_controller)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Disconnect from HomeKit devices before unloading entry."""
    hkid = entry.data["AccessoryPairingID"]

    if hkid in menuai.data[KNOWN_DEVICES]:
        connection: HKDevice = menuai.data[KNOWN_DEVICES][hkid]
        await connection.async_unload()

    return True


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Cleanup caches before removing config entry."""
    hkid = entry.data["AccessoryPairingID"]

    controller = await async_get_controller(menuai)

    # Remove the pairing on the device, making the device discoverable again.
    # Don't reuse any objects in menuai.data as they are already unloaded
    controller.load_pairing(hkid, dict(entry.data))
    try:
        await controller.remove_pairing(hkid)
    except aiohomekit.AccessoryDisconnectedError:
        _LOGGER.warning(
            (
                "Accessory %s was removed from menuai but was not reachable "
                "to properly unpair. It may need resetting before you can use it with "
                "HomeKit again"
            ),
            entry.title,
        )


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove homekit_controller config entry from a device."""
    hkid = config_entry.data["AccessoryPairingID"]
    connection: HKDevice = menuai.data[KNOWN_DEVICES][hkid]
    return not device_entry.identifiers.intersection(
        identifier
        for accessory in connection.entity_map.accessories
        for identifier in connection.device_info_for_accessory(accessory)[
            ATTR_IDENTIFIERS
        ]
    )
