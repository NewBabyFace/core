"""The Voice over IP integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging

from voip_utils import SIP_PORT

from menuai.auth.const import GROUP_ID_USER
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import CONF_SIP_PORT, DOMAIN
from .devices import VoIPDevices
from .voip import menuaiVoipDatagramProtocol

PLATFORMS = (
    Platform.ASSIST_SATELLITE,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
)
_LOGGER = logging.getLogger(__name__)
_IP_WILDCARD = "0.0.0.0"

__all__ = [
    "DOMAIN",
    "async_remove_config_entry_device",
    "async_setup_entry",
    "async_unload_entry",
]


@dataclass
class DomainData:
    """Domain data."""

    transport: asyncio.DatagramTransport
    protocol: menuaiVoipDatagramProtocol
    devices: VoIPDevices


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up VoIP integration from a config entry."""
    # Make sure there is a valid user ID for VoIP in the config entry
    if (
        "user" not in entry.data
        or (await menuai.auth.async_get_user(entry.data["user"])) is None
    ):
        voip_user = await menuai.auth.async_create_system_user(
            "Voice over IP", group_ids=[GROUP_ID_USER]
        )
        menuai.config_entries.async_update_entry(
            entry, data={**entry.data, "user": voip_user.id}
        )

    sip_port = entry.options.get(CONF_SIP_PORT, SIP_PORT)
    devices = VoIPDevices(menuai, entry)
    devices.async_setup()
    transport, protocol = await _create_sip_server(
        menuai,
        lambda: menuaiVoipDatagramProtocol(menuai, devices),
        sip_port,
    )
    _LOGGER.debug("Listening for VoIP calls on port %s", sip_port)

    menuai.data[DOMAIN] = DomainData(transport, protocol, devices)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(menuai: menuai, entry: ConfigEntry):
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def _create_sip_server(
    menuai: menuai,
    protocol_factory: Callable[
        [],
        asyncio.DatagramProtocol,
    ],
    sip_port: int,
) -> tuple[asyncio.DatagramTransport, menuaiVoipDatagramProtocol]:
    transport, protocol = await menuai.loop.create_datagram_endpoint(
        protocol_factory,
        local_addr=(_IP_WILDCARD, sip_port),
    )

    if not isinstance(protocol, menuaiVoipDatagramProtocol):
        raise TypeError(f"Expected menuaiVoipDatagramProtocol, got {protocol}")

    return transport, protocol


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload VoIP."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        _LOGGER.debug("Shutting down VoIP server")
        data = menuai.data.pop(DOMAIN)
        data.transport.close()
        await data.protocol.wait_closed()
        _LOGGER.debug("VoIP server shut down successfully")

    return unload_ok


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove device from a config entry."""
    return True


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Remove VoIP entry."""
    if "user" in entry.data and (
        user := await menuai.auth.async_get_user(entry.data["user"])
    ):
        await menuai.auth.async_remove_user(user)
