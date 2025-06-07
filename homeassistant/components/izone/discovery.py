"""Internal discovery service for  iZone AC."""

import logging

import pizone

from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import (
    DATA_DISCOVERY_SERVICE,
    DISPATCH_CONTROLLER_DISCONNECTED,
    DISPATCH_CONTROLLER_DISCOVERED,
    DISPATCH_CONTROLLER_RECONNECTED,
    DISPATCH_CONTROLLER_UPDATE,
    DISPATCH_ZONE_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


class DiscoveryService(pizone.Listener):
    """Discovery data and interfacing with pizone library."""

    def __init__(self, menuai: menuai) -> None:
        """Initialise discovery service."""
        super().__init__()
        self.menuai = menuai
        self.pi_disco: pizone.DiscoveryService | None = None

    # Listener interface
    def controller_discovered(self, ctrl: pizone.Controller) -> None:
        """Handle new controller discoverery."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_DISCOVERED, ctrl)

    def controller_disconnected(self, ctrl: pizone.Controller, ex: Exception) -> None:
        """On disconnect from controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_DISCONNECTED, ctrl, ex)

    def controller_reconnected(self, ctrl: pizone.Controller) -> None:
        """On reconnect to controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_RECONNECTED, ctrl)

    def controller_update(self, ctrl: pizone.Controller) -> None:
        """System update message is received from the controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_UPDATE, ctrl)

    def zone_update(self, ctrl: pizone.Controller, zone: pizone.Zone) -> None:
        """Zone update message is received from the controller."""
        async_dispatcher_send(self.menuai, DISPATCH_ZONE_UPDATE, ctrl, zone)


async def async_start_discovery_service(menuai: menuai):
    """Set up the pizone internal discovery."""
    if disco := menuai.data.get(DATA_DISCOVERY_SERVICE):
        # Already started
        return disco
    _LOGGER.debug("Starting iZone Discovery Service")

    # discovery local services
    disco = DiscoveryService(menuai)
    menuai.data[DATA_DISCOVERY_SERVICE] = disco

    # Start the pizone discovery service, disco is the listener
    session = aiohttp_client.async_get_clientsession(menuai)
    disco.pi_disco = pizone.discovery(disco, session=session)
    await disco.pi_disco.start_discovery()

    return disco


async def async_stop_discovery_service(menuai: menuai):
    """Stop the discovery service."""
    if not (disco := menuai.data.get(DATA_DISCOVERY_SERVICE)):
        return

    await disco.pi_disco.close()
    del menuai.data[DATA_DISCOVERY_SERVICE]

    _LOGGER.debug("Stopped iZone Discovery Service")
