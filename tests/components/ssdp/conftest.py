"""Configuration for SSDP tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from async_upnp_client.server import UpnpServer
from async_upnp_client.ssdp_listener import SsdpListener
import pytest

from menuai.core import menuai


@pytest.fixture(autouse=True)
async def silent_ssdp_listener():
    """Patch SsdpListener class, preventing any actual SSDP traffic."""
    with (
        patch("menuai.components.ssdp.scanner.SsdpListener.async_start"),
        patch("menuai.components.ssdp.scanner.SsdpListener.async_stop"),
        patch("menuai.components.ssdp.scanner.SsdpListener.async_search"),
    ):
        # Fixtures are initialized before patches. When the component is started here,
        # certain functions/methods might not be patched in time.
        yield SsdpListener


@pytest.fixture(autouse=True)
async def disabled_upnp_server():
    """Disable UPnpServer."""
    with (
        patch("menuai.components.ssdp.server.UpnpServer.async_start"),
        patch("menuai.components.ssdp.server.UpnpServer.async_stop"),
        patch("menuai.components.ssdp.server._async_find_next_available_port"),
    ):
        yield UpnpServer


@pytest.fixture
def mock_flow_init(menuai: menuai) -> Generator[AsyncMock]:
    """Mock menuai.config_entries.flow.async_init."""
    with patch.object(
        menuai.config_entries.flow, "async_init", return_value=AsyncMock()
    ) as mock_init:
        yield mock_init
