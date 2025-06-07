"""Tests for the Openhome config flow module."""

from menuai.components.openhome.const import DOMAIN
from menuai.config_entries import SOURCE_SSDP
from menuai.const import CONF_HOST, CONF_NAME, CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from tests.common import MockConfigEntry

MOCK_UDN = "uuid:4c494e4e-1234-ab12-abcd-01234567819f"
MOCK_FRIENDLY_NAME = "Test Client"
MOCK_SSDP_LOCATION = "http://device:12345/description.xml"

MOCK_DISCOVER = SsdpServiceInfo(
    ssdp_usn="usn",
    ssdp_st="st",
    ssdp_location=MOCK_SSDP_LOCATION,
    upnp={ATTR_UPNP_FRIENDLY_NAME: MOCK_FRIENDLY_NAME, ATTR_UPNP_UDN: MOCK_UDN},
)


async def test_ssdp(menuai: menuai) -> None:
    """Test a ssdp import flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=MOCK_DISCOVER,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"] == {CONF_NAME: MOCK_FRIENDLY_NAME}

    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["title"] == MOCK_FRIENDLY_NAME
    assert result2["data"] == {CONF_HOST: MOCK_SSDP_LOCATION}


async def test_device_exists(menuai: menuai) -> None:
    """Test a ssdp import where device already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: MOCK_SSDP_LOCATION},
        title=MOCK_FRIENDLY_NAME,
        unique_id=MOCK_UDN,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=MOCK_DISCOVER,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_missing_udn(menuai: menuai) -> None:
    """Test a ssdp import where discovery is missing udn."""
    broken_discovery = SsdpServiceInfo(
        ssdp_usn="usn",
        ssdp_st="st",
        ssdp_location=MOCK_SSDP_LOCATION,
        upnp={
            ATTR_UPNP_FRIENDLY_NAME: MOCK_FRIENDLY_NAME,
        },
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=broken_discovery,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "incomplete_discovery"


async def test_missing_ssdp_location(menuai: menuai) -> None:
    """Test a ssdp import where discovery is missing udn."""
    broken_discovery = SsdpServiceInfo(
        ssdp_usn="usn",
        ssdp_st="st",
        ssdp_location="",
        upnp={ATTR_UPNP_FRIENDLY_NAME: MOCK_FRIENDLY_NAME, ATTR_UPNP_UDN: MOCK_UDN},
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=broken_discovery,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "incomplete_discovery"


async def test_host_updated(menuai: menuai) -> None:
    """Test a ssdp import flow where host changes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "old_host"},
        title=MOCK_FRIENDLY_NAME,
        unique_id=MOCK_UDN,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_SSDP},
        data=MOCK_DISCOVER,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    assert entry.data[CONF_HOST] == MOCK_SSDP_LOCATION
