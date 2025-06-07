"""Test the Azure storage config flow."""

from unittest.mock import AsyncMock, MagicMock

from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError
import pytest

from menuai.components.azure_storage.const import (
    CONF_ACCOUNT_NAME,
    CONF_CONTAINER_NAME,
    CONF_STORAGE_ACCOUNT_KEY,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER, ConfigFlowResult
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import setup_integration
from .const import USER_INPUT

from tests.common import MockConfigEntry


async def __async_start_flow(
    menuai: menuai,
) -> ConfigFlowResult:
    """Initialize the  config flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM

    return await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )


async def test_flow(
    menuai: menuai,
    mock_client: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test config flow."""
    mock_client.exists.return_value = False
    result = await __async_start_flow(menuai)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result["title"]
        == f"{USER_INPUT[CONF_ACCOUNT_NAME]}/{USER_INPUT[CONF_CONTAINER_NAME]}"
    )
    assert result["data"] == {
        CONF_ACCOUNT_NAME: "account",
        CONF_CONTAINER_NAME: "container1",
        CONF_STORAGE_ACCOUNT_KEY: "test",
    }


@pytest.mark.parametrize(
    ("exception", "errors"),
    [
        (ResourceNotFoundError, {"base": "cannot_connect"}),
        (ClientAuthenticationError, {CONF_STORAGE_ACCOUNT_KEY: "invalid_auth"}),
        (Exception, {"base": "unknown"}),
    ],
)
async def test_flow_errors(
    menuai: menuai,
    mock_client: MagicMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    errors: dict[str, str],
) -> None:
    """Test config flow errors."""
    mock_client.exists.side_effect = exception

    result = await __async_start_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    # fix and finish the test
    mock_client.exists.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result["title"]
        == f"{USER_INPUT[CONF_ACCOUNT_NAME]}/{USER_INPUT[CONF_CONTAINER_NAME]}"
    )
    assert result["data"] == {
        CONF_ACCOUNT_NAME: "account",
        CONF_CONTAINER_NAME: "container1",
        CONF_STORAGE_ACCOUNT_KEY: "test",
    }


async def test_abort_if_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we abort if the account is already configured."""
    mock_config_entry.add_to_menuai(menuai)

    result = await __async_start_flow(menuai)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the reauth flow works."""

    await setup_integration(menuai, mock_config_entry)

    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STORAGE_ACCOUNT_KEY: "new_key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        **USER_INPUT,
        CONF_STORAGE_ACCOUNT_KEY: "new_key",
    }


async def test_reauth_flow_errors(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the reauth flow works with an errors."""

    await setup_integration(menuai, mock_config_entry)

    mock_client.exists.side_effect = Exception()

    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STORAGE_ACCOUNT_KEY: "new_key"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}

    # fix the error and finish the flow successfully
    mock_client.exists.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STORAGE_ACCOUNT_KEY: "new_key"}
    )
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        **USER_INPUT,
        CONF_STORAGE_ACCOUNT_KEY: "new_key",
    }


async def test_reconfigure_flow(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the reconfigure flow works."""

    mock_config_entry.add_to_menuai(menuai)
    result = await mock_config_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONTAINER_NAME: "new_container"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {
        **USER_INPUT,
        CONF_CONTAINER_NAME: "new_container",
    }
