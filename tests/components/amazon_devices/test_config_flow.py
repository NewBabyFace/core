"""Tests for the Amazon Devices config flow."""

from unittest.mock import AsyncMock

from aioamazondevices.exceptions import CannotAuthenticate, CannotConnect
import pytest

from menuai.components.amazon_devices.const import CONF_LOGIN_DATA, DOMAIN
from menuai.config_entries import SOURCE_DHCP, SOURCE_USER
from menuai.const import CONF_CODE, CONF_COUNTRY, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from .const import TEST_CODE, TEST_COUNTRY, TEST_PASSWORD, TEST_USERNAME

from tests.common import MockConfigEntry

DHCP_DISCOVERY = DhcpServiceInfo(
    ip="1.1.1.1",
    hostname="",
    macaddress="c095cfebf19f",
)


async def test_full_flow(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test full flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: TEST_COUNTRY,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_CODE: TEST_CODE,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USERNAME
    assert result["data"] == {
        CONF_COUNTRY: TEST_COUNTRY,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_LOGIN_DATA: {
            "customer_info": {"user_id": TEST_USERNAME},
        },
    }
    assert result["result"].unique_id == TEST_USERNAME
    mock_amazon_devices_client.login_mode_interactive.assert_called_once_with("023123")


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (CannotConnect, "cannot_connect"),
        (CannotAuthenticate, "invalid_auth"),
    ],
)
async def test_flow_errors(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test flow errors."""
    mock_amazon_devices_client.login_mode_interactive.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: TEST_COUNTRY,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_CODE: TEST_CODE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_amazon_devices_client.login_mode_interactive.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: TEST_COUNTRY,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_CODE: TEST_CODE,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test duplicate flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: TEST_COUNTRY,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_CODE: TEST_CODE,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_dhcp_flow(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test full DHCP flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DHCP_DISCOVERY,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: TEST_COUNTRY,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_CODE: TEST_CODE,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USERNAME
    assert result["data"] == {
        CONF_COUNTRY: TEST_COUNTRY,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_LOGIN_DATA: {
            "customer_info": {"user_id": TEST_USERNAME},
        },
    }
    assert result["result"].unique_id == TEST_USERNAME


async def test_dhcp_already_configured(
    menuai: menuai,
    mock_amazon_devices_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test duplicate flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DHCP_DISCOVERY,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
