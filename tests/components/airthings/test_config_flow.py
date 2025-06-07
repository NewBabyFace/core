"""Test the Airthings config flow."""

from unittest.mock import patch

import airthings
import pytest

from menuai import config_entries
from menuai.components.airthings.const import CONF_SECRET, DOMAIN
from menuai.const import CONF_ID
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from tests.common import MockConfigEntry

TEST_DATA = {
    CONF_ID: "client_id",
    CONF_SECRET: "secret",
}

DHCP_SERVICE_INFO = [
    DhcpServiceInfo(
        hostname="airthings-view",
        ip="192.168.1.100",
        macaddress="00:00:00:00:00:00",
    ),
    DhcpServiceInfo(
        hostname="airthings-hub",
        ip="192.168.1.101",
        macaddress="D0:14:11:90:00:00",
    ),
    DhcpServiceInfo(
        hostname="airthings-hub",
        ip="192.168.1.102",
        macaddress="70:B3:D5:2A:00:00",
    ),
]


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "airthings.get_token",
            return_value="test_token",
        ),
        patch(
            "menuai.components.airthings.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_DATA,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Airthings"
    assert result["data"] == TEST_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "airthings.get_token",
        side_effect=airthings.AirthingsAuthError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "airthings.get_token",
        side_effect=airthings.AirthingsConnectionError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(menuai: menuai) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "airthings.get_token",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_flow_entry_already_exists(menuai: menuai) -> None:
    """Test user input for config_entry that already exists."""

    first_entry = MockConfigEntry(
        domain="airthings",
        data=TEST_DATA,
        unique_id=TEST_DATA[CONF_ID],
    )
    first_entry.add_to_menuai(menuai)

    with patch("airthings.get_token", return_value="token"):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=TEST_DATA
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize("dhcp_service_info", DHCP_SERVICE_INFO)
async def test_dhcp_flow(
    menuai: menuai, dhcp_service_info: DhcpServiceInfo
) -> None:
    """Test the DHCP discovery flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=dhcp_service_info,
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.airthings.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "airthings.get_token",
            return_value="test_token",
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_DATA,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Airthings"
    assert result["data"] == TEST_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_dhcp_flow_hub_already_configured(menuai: menuai) -> None:
    """Test that DHCP discovery fails when already configured."""

    first_entry = MockConfigEntry(
        domain="airthings",
        data=TEST_DATA,
        unique_id=TEST_DATA[CONF_ID],
    )
    first_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=DHCP_SERVICE_INFO[0],
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
