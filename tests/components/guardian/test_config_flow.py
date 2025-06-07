"""Define tests for the Elexa Guardian config flow."""

from ipaddress import ip_address
from typing import Any
from unittest.mock import patch

from aioguardian.errors import GuardianError
import pytest

from menuai.components.guardian import CONF_UID, DOMAIN
from menuai.components.guardian.config_flow import (
    async_get_pin_from_discovery_hostname,
    async_get_pin_from_uid,
)
from menuai.config_entries import SOURCE_DHCP, SOURCE_USER, SOURCE_ZEROCONF
from menuai.const import CONF_IP_ADDRESS, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.mark.usefixtures("config_entry", "setup_guardian")
async def test_duplicate_error(menuai: menuai, config: dict[str, Any]) -> None:
    """Test that errors are shown when duplicate entries are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_connect_error(menuai: menuai, config: dict[str, Any]) -> None:
    """Test that the config entry errors out if the device cannot connect."""
    with patch(
        "aioguardian.client.Client.connect",
        side_effect=GuardianError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=config
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_IP_ADDRESS: "cannot_connect"}


async def test_get_pin_from_discovery_hostname() -> None:
    """Test getting a device PIN from the zeroconf-discovered hostname."""
    pin = async_get_pin_from_discovery_hostname("GVC1-3456.local.")
    assert pin == "3456"


async def test_get_pin_from_uid() -> None:
    """Test getting a device PIN from its UID."""
    pin = async_get_pin_from_uid("ABCDEF123456")
    assert pin == "3456"


@pytest.mark.usefixtures("setup_guardian")
async def test_step_user(menuai: menuai, config: dict[str, Any]) -> None:
    """Test the user step."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ABCDEF123456"
    assert result["data"] == {
        CONF_IP_ADDRESS: "192.168.1.100",
        CONF_PORT: 7777,
        CONF_UID: "ABCDEF123456",
    }


@pytest.mark.usefixtures("setup_guardian")
async def test_step_zeroconf(menuai: menuai) -> None:
    """Test the zeroconf step."""
    zeroconf_data = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.100"),
        ip_addresses=[ip_address("192.168.1.100")],
        port=7777,
        hostname="GVC1-ABCD.local.",
        type="_api._udp.local.",
        name="Guardian Valve Controller API._api._udp.local.",
        properties={"_raw": {}},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_data
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ABCDEF123456"
    assert result["data"] == {
        CONF_IP_ADDRESS: "192.168.1.100",
        CONF_PORT: 7777,
        CONF_UID: "ABCDEF123456",
    }


async def test_step_zeroconf_already_in_progress(menuai: menuai) -> None:
    """Test the zeroconf step aborting because it's already in progress."""
    zeroconf_data = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.100"),
        ip_addresses=[ip_address("192.168.1.100")],
        port=7777,
        hostname="GVC1-ABCD.local.",
        type="_api._udp.local.",
        name="Guardian Valve Controller API._api._udp.local.",
        properties={"_raw": {}},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_data
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=zeroconf_data
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


@pytest.mark.usefixtures("setup_guardian")
async def test_step_dhcp(menuai: menuai) -> None:
    """Test the dhcp step."""
    dhcp_data = DhcpServiceInfo(
        ip="192.168.1.100",
        hostname="GVC1-ABCD.local.",
        macaddress="aabbccddeeff",
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=dhcp_data
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ABCDEF123456"
    assert result["data"] == {
        CONF_IP_ADDRESS: "192.168.1.100",
        CONF_PORT: 7777,
        CONF_UID: "ABCDEF123456",
    }


async def test_step_dhcp_already_in_progress(menuai: menuai) -> None:
    """Test the zeroconf step aborting because it's already in progress."""
    dhcp_data = DhcpServiceInfo(
        ip="192.168.1.100",
        hostname="GVC1-ABCD.local.",
        macaddress="aabbccddeeff",
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=dhcp_data
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=dhcp_data
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_step_dhcp_already_setup_match_mac(menuai: menuai) -> None:
    """Test we abort if the device is already setup with matching unique id and discovered via DHCP."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_IP_ADDRESS: "1.2.3.4"}, unique_id="guardian_ABCD"
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip="192.168.1.100",
            hostname="GVC1-ABCD.local.",
            macaddress="aabbccddabcd",
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_dhcp_already_setup_match_ip(menuai: menuai) -> None:
    """Test we abort if the device is already setup with matching ip and discovered via DHCP."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_IP_ADDRESS: "192.168.1.100"},
        unique_id="guardian_0000",
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip="192.168.1.100",
            hostname="GVC1-ABCD.local.",
            macaddress="aabbccddabcd",
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
