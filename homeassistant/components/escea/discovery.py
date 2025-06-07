"""Internal discovery service for  Escea Fireplace."""

from __future__ import annotations

from pescea import (
    AbstractDiscoveryService,
    Controller,
    Listener,
    discovery_service as pescea_discovery_service,
)

from menuai.core import menuai
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import (
    DATA_DISCOVERY_SERVICE,
    DISPATCH_CONTROLLER_DISCONNECTED,
    DISPATCH_CONTROLLER_DISCOVERED,
    DISPATCH_CONTROLLER_RECONNECTED,
    DISPATCH_CONTROLLER_UPDATE,
)


class DiscoveryServiceListener(Listener):
    """Discovery data and interfacing with pescea library."""

    def __init__(self, menuai: menuai) -> None:
        """Initialise discovery service."""
        super().__init__()
        self.menuai = menuai

    # Listener interface
    def controller_discovered(self, ctrl: Controller) -> None:
        """Handle new controller discoverery."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_DISCOVERED, ctrl)

    def controller_disconnected(self, ctrl: Controller, ex: Exception) -> None:
        """On disconnect from controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_DISCONNECTED, ctrl, ex)

    def controller_reconnected(self, ctrl: Controller) -> None:
        """On reconnect to controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_RECONNECTED, ctrl)

    def controller_update(self, ctrl: Controller) -> None:
        """System update message is received from the controller."""
        async_dispatcher_send(self.menuai, DISPATCH_CONTROLLER_UPDATE, ctrl)


async def async_start_discovery_service(
    menuai: menuai,
) -> AbstractDiscoveryService:
    """Set up the pescea internal discovery."""
    discovery_service = menuai.data.get(DATA_DISCOVERY_SERVICE)
    if discovery_service:
        # Already started
        return discovery_service

    # discovery local services
    listener = DiscoveryServiceListener(menuai)
    discovery_service = pescea_discovery_service(listener)
    menuai.data[DATA_DISCOVERY_SERVICE] = discovery_service

    await discovery_service.start_discovery()

    return discovery_service


async def async_stop_discovery_service(menuai: menuai) -> None:
    """Stop the discovery service."""
    discovery_service = menuai.data.get(DATA_DISCOVERY_SERVICE)
    if not discovery_service:
        return

    await discovery_service.close()
    del menuai.data[DATA_DISCOVERY_SERVICE]
