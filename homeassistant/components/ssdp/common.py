"""Common functions for SSDP discovery."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address

from menuai.components import network
from menuai.core import menuai


async def async_build_source_set(menuai: menuai) -> set[IPv4Address | IPv6Address]:
    """Build the list of ssdp sources."""
    return {
        source_ip
        for source_ip in await network.async_get_enabled_source_ips(menuai)
        if not source_ip.is_loopback
        and not source_ip.is_global
        and ((source_ip.version == 6 and source_ip.scope_id) or source_ip.version == 4)
    }
