"""Refoss helpers functions."""

from __future__ import annotations

from refoss_ha.discovery import Discovery

from menuai.core import menuai
from menuai.helpers import singleton


@singleton.singleton("refoss_discovery_server")
async def refoss_discovery_server(menuai: menuai) -> Discovery:
    """Get refoss Discovery server."""
    discovery_server = Discovery()
    await discovery_server.initialize()
    return discovery_server
