"""Tests for the SSDP integration."""

from __future__ import annotations

from datetime import datetime

from async_upnp_client.ssdp import udn_from_headers
from async_upnp_client.ssdp_listener import SsdpListener
from async_upnp_client.utils import CaseInsensitiveDict

from menuai.components import ssdp
from menuai.core import menuai
from menuai.setup import async_setup_component


async def init_ssdp_component(menuai: menuai) -> SsdpListener:
    """Initialize ssdp component and get SsdpListener."""
    await async_setup_component(menuai, ssdp.DOMAIN, {ssdp.DOMAIN: {}})
    await menuai.async_block_till_done()
    return menuai.data[ssdp.DOMAIN][ssdp.SSDP_SCANNER]._ssdp_listeners[0]


def _ssdp_headers(headers) -> CaseInsensitiveDict:
    """Create a CaseInsensitiveDict with headers and a timestamp."""
    ssdp_headers = CaseInsensitiveDict(headers, _timestamp=datetime.now())
    ssdp_headers["_udn"] = udn_from_headers(ssdp_headers)
    return ssdp_headers
