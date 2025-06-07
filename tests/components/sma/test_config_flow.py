"""Test the sma config flow."""

from unittest.mock import AsyncMock, patch

from pysma.exceptions import (
    SmaAuthenticationException,
    SmaConnectionException,
    SmaReadException,
)
import pytest

from menuai.components.sma.const import DOMAIN
from menuai.config_entries import SOURCE_DHCP, SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from . import (
    MOCK_DEVICE,
    MOCK_DHCP_DISCOVERY,
    MOCK_DHCP_DISCOVERY_INPUT,
    MOCK_USER_INPUT,
    MOCK_USER_REAUTH,
)

from tests.conftest import MockConfigEntry

DHCP_DISCOVERY = DhcpServiceInfo(
    ip="1.1.1.1",
    hostname="SMA123456",
    macaddress="0015BB00abcd",
)

DHCP_DISCOVERY_DUPLICATE = DhcpServiceInfo(
    ip="1.1.1.1",
    hostname="SMA123456789",
    macaddress="0015BB00abcd",
)


async def test_form(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_sma_client: AsyncMock
) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USER_INPUT["host"]
    assert result["data"] == MOCK_USER_INPUT

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (SmaConnectionException, "cannot_connect"),
        (SmaAuthenticationException, "invalid_auth"),
        (SmaReadException, "cannot_retrieve_device_info"),
        (Exception, "unknown"),
    ],
)
async def test_form_exceptions(
    menuai: menuai,
    mock_setup_entry: MockConfigEntry,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.sma.pysma.SMA.new_session", side_effect=exception
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_form_already_configured(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_sma_client: AsyncMock
) -> None:
    """Test starting a flow by user when already configured."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT, unique_id="123456789")
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_dhcp_discovery(
    menuai: menuai, mock_setup_entry: MockConfigEntry, mock_sma_client: AsyncMock
) -> None:
    """Test we can setup from dhcp discovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DHCP_DISCOVERY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DHCP_DISCOVERY_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DHCP_DISCOVERY["host"]
    assert result["data"] == MOCK_DHCP_DISCOVERY
    assert result["result"].unique_id == DHCP_DISCOVERY.hostname.replace("SMA", "")


async def test_dhcp_already_configured(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test starting a flow by dhcp when already configured."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP_DISCOVERY_DUPLICATE
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (SmaConnectionException, "cannot_connect"),
        (SmaAuthenticationException, "invalid_auth"),
        (SmaReadException, "cannot_retrieve_device_info"),
        (Exception, "unknown"),
    ],
)
async def test_dhcp_exceptions(
    menuai: menuai,
    mock_setup_entry: MockConfigEntry,
    mock_sma_client: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle cannot connect error in DHCP flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DHCP_DISCOVERY,
    )

    with patch("menuai.components.sma.pysma.SMA") as mock_sma:
        mock_sma_instance = mock_sma.return_value
        mock_sma_instance.new_session = AsyncMock(side_effect=exception)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DHCP_DISCOVERY_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    with patch("menuai.components.sma.pysma.SMA") as mock_sma:
        mock_sma_instance = mock_sma.return_value
        mock_sma_instance.new_session = AsyncMock(return_value=True)
        mock_sma_instance.device_info = AsyncMock(return_value=MOCK_DEVICE)
        mock_sma_instance.close_session = AsyncMock(return_value=True)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DHCP_DISCOVERY_INPUT,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DHCP_DISCOVERY["host"]
    assert result["data"] == MOCK_DHCP_DISCOVERY
    assert result["result"].unique_id == DHCP_DISCOVERY.hostname.replace("SMA", "")


async def test_full_flow_reauth(
    menuai: menuai, mock_setup_entry: MockConfigEntry, mock_sma_client: AsyncMock
) -> None:
    """Test the full flow of the config flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT, unique_id="123456789")
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # There is no user input
    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USER_REAUTH,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (SmaConnectionException, "cannot_connect"),
        (SmaAuthenticationException, "invalid_auth"),
        (SmaReadException, "cannot_retrieve_device_info"),
        (Exception, "unknown"),
    ],
)
async def test_reauth_flow_exceptions(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle errors during reauth flow properly."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT, unique_id="123456789")
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with patch("menuai.components.sma.pysma.SMA") as mock_sma:
        mock_sma_instance = mock_sma.return_value
        mock_sma_instance.new_session = AsyncMock(side_effect=exception)
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_REAUTH,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": error}
        assert result["step_id"] == "reauth_confirm"

        mock_sma_instance.new_session = AsyncMock(return_value=True)
        mock_sma_instance.device_info = AsyncMock(return_value=MOCK_DEVICE)
        mock_sma_instance.close_session = AsyncMock(return_value=True)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_REAUTH,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
