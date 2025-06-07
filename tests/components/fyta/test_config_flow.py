"""Test the fyta config flow."""

from unittest.mock import AsyncMock

from fyta_cli.fyta_exceptions import (
    FytaAuthentificationError,
    FytaConnectionError,
    FytaPasswordError,
)
import pytest

from menuai import config_entries
from menuai.components.fyta.const import CONF_EXPIRATION, DOMAIN
from menuai.const import CONF_ACCESS_TOKEN, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from .const import ACCESS_TOKEN, EXPIRATION, PASSWORD, USERNAME

from tests.common import MockConfigEntry


async def user_step(
    menuai: menuai, flow_id: str, mock_setup_entry: AsyncMock
) -> None:
    """Test user step (helper function)."""

    result = await menuai.config_entries.flow.async_configure(
        flow_id, {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"] == {
        CONF_USERNAME: USERNAME,
        CONF_PASSWORD: PASSWORD,
        CONF_ACCESS_TOKEN: ACCESS_TOKEN,
        CONF_EXPIRATION: EXPIRATION,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow(
    menuai: menuai, mock_fyta_connector: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    await user_step(menuai, result["flow_id"], mock_setup_entry)


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (FytaConnectionError, {"base": "cannot_connect"}),
        (FytaAuthentificationError, {"base": "invalid_auth"}),
        (FytaPasswordError, {"base": "invalid_auth", CONF_PASSWORD: "password_error"}),
        (Exception, {"base": "unknown"}),
    ],
)
async def test_form_exceptions(
    menuai: menuai,
    exception: Exception,
    error: dict[str, str],
    mock_fyta_connector: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we can handle Form exceptions."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_fyta_connector.login.side_effect = exception

    # tests with connection error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == error

    mock_fyta_connector.login.side_effect = None

    # tests with all information provided
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_ACCESS_TOKEN] == ACCESS_TOKEN
    assert result["data"][CONF_EXPIRATION] == EXPIRATION

    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_entry(
    menuai: menuai, mock_fyta_connector: AsyncMock
) -> None:
    """Test duplicate setup handling."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (FytaConnectionError, {"base": "cannot_connect"}),
        (FytaAuthentificationError, {"base": "invalid_auth"}),
        (FytaPasswordError, {"base": "invalid_auth", CONF_PASSWORD: "password_error"}),
        (Exception, {"base": "unknown"}),
    ],
)
async def test_reauth(
    menuai: menuai,
    exception: Exception,
    error: dict[str, str],
    mock_fyta_connector: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reauth-flow works."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=USERNAME,
        data={
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_ACCESS_TOKEN: ACCESS_TOKEN,
            CONF_EXPIRATION: EXPIRATION,
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_fyta_connector.login.side_effect = exception

    # tests with connection error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == error

    mock_fyta_connector.login.side_effect = None

    # tests with all information provided
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: "other_username", CONF_PASSWORD: "other_password"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "other_username"
    assert entry.data[CONF_PASSWORD] == "other_password"
    assert entry.data[CONF_ACCESS_TOKEN] == ACCESS_TOKEN
    assert entry.data[CONF_EXPIRATION] == EXPIRATION


async def test_dhcp_discovery(
    menuai: menuai, mock_fyta_connector: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test DHCP discovery flow."""

    service_info = DhcpServiceInfo(
        hostname="FYTA HUB",
        ip="1.2.3.4",
        macaddress="aabbccddeeff",
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=service_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    await user_step(menuai, result["flow_id"], mock_setup_entry)
