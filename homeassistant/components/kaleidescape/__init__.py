"""The Kaleidescape integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from kaleidescape import Device as KaleidescapeDevice, KaleidescapeError

from menuai.const import CONF_HOST, EVENT_menuai_STOP, Platform
from menuai.exceptions import ConfigEntryNotReady, menuaiError

from .const import DOMAIN

if TYPE_CHECKING:
    from menuai.config_entries import ConfigEntry
    from menuai.core import Event, menuai

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Kaleidescape from a config entry."""
    device = KaleidescapeDevice(
        entry.data[CONF_HOST], timeout=5, reconnect=True, reconnect_delay=5
    )

    try:
        await device.connect()
    except (KaleidescapeError, ConnectionError) as err:
        await device.disconnect()
        raise ConfigEntryNotReady(
            f"Unable to connect to {entry.data[CONF_HOST]}: {err}"
        ) from err

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    async def disconnect(event: Event) -> None:
        await device.disconnect()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, disconnect)
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        await menuai.data[DOMAIN][entry.entry_id].disconnect()
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


@dataclass
class KaleidescapeDeviceInfo:
    """Metadata for a Kaleidescape device."""

    host: str
    serial: str
    name: str
    model: str
    server_only: bool


class UnsupportedError(menuaiError):
    """Error for unsupported device types."""


async def validate_host(host: str) -> KaleidescapeDeviceInfo:
    """Validate device host."""
    device = KaleidescapeDevice(host)

    try:
        await device.connect()
    except (KaleidescapeError, ConnectionError):
        await device.disconnect()
        raise

    info = KaleidescapeDeviceInfo(
        host=device.host,
        serial=device.system.serial_number,
        name=device.system.friendly_name,
        model=device.system.type,
        server_only=device.is_server_only,
    )

    await device.disconnect()

    return info
