"""Test network system health."""

import asyncio

import pytest

from menuai.components.network.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import get_system_health_info


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_network_system_health(menuai: menuai) -> None:
    """Test network system health."""

    assert await async_setup_component(menuai, "system_health", {})
    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
    info = await get_system_health_info(menuai, "network")

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "adapters": "eth0 (disabled), lo0 (disabled), eth1 (enabled, default, auto), vtun0 (disabled)",
        "announce_addresses": "192.168.1.5",
        "ipv4_addresses": "eth0 (), lo0 (127.0.0.1/8), eth1 (192.168.1.5/23), vtun0 (169.254.3.2/16)",
        "ipv6_addresses": "eth0 (2001:db8::/8), lo0 (), eth1 (), vtun0 ()",
    }
