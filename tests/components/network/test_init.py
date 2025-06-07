"""Test the Network Configuration."""

from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import network
from menuai.components.network.const import (
    ATTR_ADAPTERS,
    ATTR_CONFIGURED_ADAPTERS,
    DOMAIN,
    MDNS_TARGET_IP,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component

from . import LOOPBACK_IPADDR, NO_LOOPBACK_IPADDR

from tests.typing import WebSocketGenerator


def _mock_cond_socket(sockname):
    class CondMockSock(MagicMock):
        def connect(self, addr):
            """Mock connect that stores addr."""
            # pylint: disable-next=attribute-defined-outside-init
            self._addr = addr[0]

        def getsockname(self):
            """Return addr if it matches the mock sockname."""
            if self._addr == sockname:
                return [sockname]
            raise AttributeError

    return CondMockSock()


def _mock_socket_exception(exc):
    mock_socket = MagicMock()
    mock_socket.getsockname = Mock(side_effect=exc)
    return mock_socket


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_async_detect_interfaces_setting_non_loopback_route(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test without default interface config and the route returns a non-loopback address."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == []

    assert network_obj.adapters == [
        {
            "auto": False,
            "index": 1,
            "default": False,
            "enabled": False,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "index": 0,
            "auto": False,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "index": 2,
            "auto": True,
            "default": True,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "index": 3,
            "auto": False,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


@pytest.mark.usefixtures("mock_socket_loopback")
async def test_async_detect_interfaces_setting_loopback_route(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test without default interface config and the route returns a loopback address."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == []
    assert network_obj.adapters == [
        {
            "index": 1,
            "auto": True,
            "default": False,
            "enabled": True,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "index": 0,
            "auto": False,
            "default": True,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "index": 2,
            "auto": True,
            "default": False,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "index": 3,
            "auto": False,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


@pytest.mark.parametrize("mock_socket", [[]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_async_detect_interfaces_setting_empty_route(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test without default interface config and the route returns nothing."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == []
    assert network_obj.adapters == [
        {
            "auto": True,
            "index": 1,
            "default": False,
            "enabled": True,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "auto": False,
            "index": 0,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "auto": True,
            "index": 2,
            "default": False,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "auto": False,
            "index": 3,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


async def test_async_detect_interfaces_setting_exception(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test without default interface config and the route throws an exception."""
    with patch(
        "menuai.components.network.util.socket.socket",
        return_value=_mock_socket_exception(AttributeError),
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == []
    assert network_obj.adapters == [
        {
            "auto": True,
            "index": 1,
            "default": False,
            "enabled": True,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "auto": False,
            "index": 0,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "auto": True,
            "index": 2,
            "default": False,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "auto": False,
            "index": 3,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_interfaces_configured_from_storage(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test settings from storage are preferred over auto configure."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth0", "eth1", "vtun0"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == ["eth0", "eth1", "vtun0"]

    assert network_obj.adapters == [
        {
            "auto": False,
            "index": 1,
            "default": False,
            "enabled": True,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "auto": False,
            "index": 0,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "auto": True,
            "index": 2,
            "default": True,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "auto": False,
            "index": 3,
            "default": False,
            "enabled": True,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


async def test_interfaces_configured_from_storage_websocket_update(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    menuai_storage: dict[str, Any],
) -> None:
    """Test settings from storage can be updated via websocket api."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth0", "eth1", "vtun0"]},
    }
    with patch(
        "menuai.components.network.util.socket.socket",
        return_value=MagicMock(getsockname=Mock(return_value=[NO_LOOPBACK_IPADDR])),
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()

    network_obj = menuai.data[DOMAIN]
    assert network_obj.configured_adapters == ["eth0", "eth1", "vtun0"]
    ws_client = await menuai_ws_client(menuai)
    await ws_client.send_json({"id": 1, "type": "network"})

    response = await ws_client.receive_json()

    assert response["success"]
    assert response["result"][ATTR_CONFIGURED_ADAPTERS] == ["eth0", "eth1", "vtun0"]
    assert response["result"][ATTR_ADAPTERS] == [
        {
            "auto": False,
            "index": 1,
            "default": False,
            "enabled": True,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "auto": False,
            "index": 0,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "auto": True,
            "index": 2,
            "default": True,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "auto": False,
            "index": 3,
            "default": False,
            "enabled": True,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]

    await ws_client.send_json(
        {"id": 2, "type": "network/configure", "config": {ATTR_CONFIGURED_ADAPTERS: []}}
    )
    response = await ws_client.receive_json()
    assert response["result"][ATTR_CONFIGURED_ADAPTERS] == []

    await ws_client.send_json({"id": 3, "type": "network"})
    response = await ws_client.receive_json()
    assert response["result"][ATTR_CONFIGURED_ADAPTERS] == []
    assert response["result"][ATTR_ADAPTERS] == [
        {
            "auto": False,
            "index": 1,
            "default": False,
            "enabled": False,
            "ipv4": [],
            "ipv6": [
                {
                    "address": "2001:db8::",
                    "network_prefix": 8,
                    "flowinfo": 1,
                    "scope_id": 1,
                }
            ],
            "name": "eth0",
        },
        {
            "auto": False,
            "index": 0,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "127.0.0.1", "network_prefix": 8}],
            "ipv6": [],
            "name": "lo0",
        },
        {
            "auto": True,
            "index": 2,
            "default": True,
            "enabled": True,
            "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
            "ipv6": [],
            "name": "eth1",
        },
        {
            "auto": False,
            "index": 3,
            "default": False,
            "enabled": False,
            "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
            "ipv6": [],
            "name": "vtun0",
        },
    ]


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_async_get_source_ip_matching_interface(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test getting the source ip address with interface matching."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert await network.async_get_source_ip(menuai, MDNS_TARGET_IP) == NO_LOOPBACK_IPADDR


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_async_get_source_ip_interface_not_match(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test getting the source ip address with interface does not match."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["vtun0"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert await network.async_get_source_ip(menuai, MDNS_TARGET_IP) == "169.254.3.2"


@pytest.mark.parametrize("mock_socket", [[None]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_async_get_source_ip_cannot_determine_target(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test getting the source ip address when getsockname fails."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert await network.async_get_source_ip(menuai, MDNS_TARGET_IP) == NO_LOOPBACK_IPADDR


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_async_get_ipv4_broadcast_addresses_default(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test getting ipv4 broadcast addresses when only the default address is enabled."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert await network.async_get_ipv4_broadcast_addresses(menuai) == {
        IPv4Address("255.255.255.255")
    }


@pytest.mark.usefixtures("mock_socket_loopback")
async def test_async_get_ipv4_broadcast_addresses_multiple(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test getting ipv4 broadcast addresses when multiple adapters are enabled."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1", "vtun0"]},
    }

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert await network.async_get_ipv4_broadcast_addresses(menuai) == {
        IPv4Address("255.255.255.255"),
        IPv4Address("192.168.1.255"),
        IPv4Address("169.254.255.255"),
    }


@pytest.mark.usefixtures("mock_socket_no_loopback")
async def test_async_get_source_ip_no_enabled_addresses(
    menuai: menuai, menuai_storage: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Test getting the source ip address when all adapters are disabled."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    with patch(
        "menuai.components.network.util.ifaddr.get_adapters",
        return_value=[],
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()

        assert (
            await network.async_get_source_ip(menuai, MDNS_TARGET_IP)
            == NO_LOOPBACK_IPADDR
        )

    assert "source address detection may be inaccurate" in caplog.text


@pytest.mark.parametrize("mock_socket", [[None]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_async_get_source_ip_cannot_be_determined_and_no_enabled_addresses(
    menuai: menuai, menuai_storage: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Test getting the source ip address when all adapters are disabled and getting it fails."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    with patch(
        "menuai.components.network.util.ifaddr.get_adapters",
        return_value=[],
    ):
        assert not await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
        with pytest.raises(menuaiError):
            await network.async_get_source_ip(menuai, MDNS_TARGET_IP)


async def test_async_get_source_ip_no_ip_loopback(
    menuai: menuai, menuai_storage: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Test getting the source ip address when all adapters are disabled no target is specified."""
    menuai_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {ATTR_CONFIGURED_ADAPTERS: ["eth1"]},
    }

    with (
        patch(
            "menuai.components.network.util.ifaddr.get_adapters",
            return_value=[],
        ),
        patch(
            "menuai.components.network.util.socket.socket",
            return_value=_mock_cond_socket(LOOPBACK_IPADDR),
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()

        assert await network.async_get_source_ip(menuai) == "127.0.0.1"


_ADAPTERS_WITH_MANUAL_CONFIG = [
    {
        "auto": True,
        "index": 1,
        "default": False,
        "enabled": True,
        "ipv4": [],
        "ipv6": [
            {
                "address": "2001:db8::",
                "network_prefix": 64,
                "flowinfo": 1,
                "scope_id": 1,
            },
            {
                "address": "fe80::1234:5678:9abc:def0",
                "network_prefix": 64,
                "flowinfo": 1,
                "scope_id": 1,
            },
        ],
        "name": "eth0",
    },
    {
        "auto": True,
        "index": 2,
        "default": False,
        "enabled": True,
        "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
        "ipv6": [],
        "name": "eth1",
    },
    {
        "auto": True,
        "index": 3,
        "default": False,
        "enabled": True,
        "ipv4": [{"address": "172.16.1.5", "network_prefix": 23}],
        "ipv6": [
            {
                "address": "fe80::dead:beef:dead:beef",
                "network_prefix": 64,
                "flowinfo": 1,
                "scope_id": 3,
            }
        ],
        "name": "eth2",
    },
    {
        "auto": False,
        "index": 4,
        "default": False,
        "enabled": False,
        "ipv4": [{"address": "169.254.3.2", "network_prefix": 16}],
        "ipv6": [],
        "name": "vtun0",
    },
]


async def test_async_get_announce_addresses(menuai: menuai) -> None:
    """Test addresses for mDNS/etc announcement."""
    first_ip = "172.16.1.5"
    with (
        patch(
            "menuai.components.network.async_get_source_ip",
            return_value=first_ip,
        ),
        patch(
            "menuai.components.network.async_get_adapters",
            return_value=_ADAPTERS_WITH_MANUAL_CONFIG,
        ),
    ):
        actual = await network.async_get_announce_addresses(menuai)
    assert actual[0] == first_ip and actual == [
        first_ip,
        "2001:db8::",
        "fe80::1234:5678:9abc:def0",
        "192.168.1.5",
        "fe80::dead:beef:dead:beef",
    ]

    first_ip = "192.168.1.5"
    with (
        patch(
            "menuai.components.network.async_get_source_ip",
            return_value=first_ip,
        ),
        patch(
            "menuai.components.network.async_get_adapters",
            return_value=_ADAPTERS_WITH_MANUAL_CONFIG,
        ),
    ):
        actual = await network.async_get_announce_addresses(menuai)

    assert actual[0] == first_ip and actual == [
        first_ip,
        "2001:db8::",
        "fe80::1234:5678:9abc:def0",
        "172.16.1.5",
        "fe80::dead:beef:dead:beef",
    ]


async def test_async_get_announce_addresses_no_source_ip(menuai: menuai) -> None:
    """Test addresses for mDNS/etc announcement without source ip."""
    with (
        patch(
            "menuai.components.network.async_get_source_ip",
            return_value=None,
        ),
        patch(
            "menuai.components.network.async_get_adapters",
            return_value=_ADAPTERS_WITH_MANUAL_CONFIG,
        ),
    ):
        actual = await network.async_get_announce_addresses(menuai)
    assert actual == [
        "2001:db8::",
        "fe80::1234:5678:9abc:def0",
        "192.168.1.5",
        "172.16.1.5",
        "fe80::dead:beef:dead:beef",
    ]


async def test_websocket_network_url(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test the network/url websocket command."""
    assert await async_setup_component(menuai, "network", {})

    client = await menuai_ws_client(menuai)

    with (
        patch(
            "menuai.helpers.network._get_internal_url", return_value="internal"
        ),
        patch("menuai.helpers.network._get_cloud_url", return_value="cloud"),
    ):
        await client.send_json({"id": 1, "type": "network/url"})
        msg = await client.receive_json()
        assert msg["success"]
        assert msg["result"] == {
            "internal": "internal",
            "external": "cloud",
            "cloud": "cloud",
        }

    # Test with no cloud URL
    with (
        patch(
            "menuai.helpers.network._get_internal_url", return_value="internal"
        ),
    ):
        await client.send_json({"id": 2, "type": "network/url"})
        msg = await client.receive_json()
        assert msg["success"]
        assert msg["result"] == {
            "internal": "internal",
            "external": None,
            "cloud": None,
        }


@pytest.mark.parametrize("mock_socket", [[]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_repair_docker_host_network_not_docker(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test repair is not created when not in Docker."""
    with patch("menuai.util.package.is_docker_env", return_value=False):
        assert await async_setup_component(menuai, "network", {})

    assert not issue_registry.async_get_issue(DOMAIN, "docker_host_network")


@pytest.mark.parametrize("mock_socket", [[]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_repair_docker_host_network_with_host_networking(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test repair is not created when in Docker with host networking."""
    with (
        patch("menuai.util.package.is_docker_env", return_value=True),
        patch("menuai.components.network.Path.exists", return_value=True),
    ):
        assert await async_setup_component(menuai, "network", {})

    assert not issue_registry.async_get_issue(DOMAIN, "docker_host_network")


@pytest.mark.parametrize("mock_socket", [[]], indirect=True)
@pytest.mark.usefixtures("mock_socket")
async def test_repair_docker_host_network_without_host_networking(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test repair is created when in Docker without host networking."""
    with (
        patch("menuai.util.package.is_docker_env", return_value=True),
        patch("menuai.components.network.Path.exists", return_value=False),
    ):
        assert await async_setup_component(menuai, "network", {})

    assert (issue := issue_registry.async_get_issue(DOMAIN, "docker_host_network"))
    assert issue == snapshot
