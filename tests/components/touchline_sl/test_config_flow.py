"""Test the Roth Touchline SL config flow."""

from unittest.mock import AsyncMock

import pytest
from pytouchlinesl.client import RothAPIError

from menuai.components.touchline_sl.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

RESULT_UNIQUE_ID = "12345"

CONFIG_DATA = {
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
}


async def test_config_flow_success(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_touchlinesl_client: AsyncMock
) -> None:
    """Test the happy path where the provided username/password result in a new entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], CONFIG_DATA
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"] == CONFIG_DATA
    assert result["result"].unique_id == RESULT_UNIQUE_ID
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error_base"),
    [
        (RothAPIError(status=401), "invalid_auth"),
        (RothAPIError(status=502), "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_config_flow_failure_api_exceptions(
    menuai: menuai,
    exception: Exception,
    error_base: str,
    mock_setup_entry: AsyncMock,
    mock_touchlinesl_client: AsyncMock,
) -> None:
    """Test for invalid credentials or API connection errors, and that the form can recover."""
    mock_touchlinesl_client.user_id.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], CONFIG_DATA
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error_base}

    # "Fix" the problem, and try again.
    mock_touchlinesl_client.user_id.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], CONFIG_DATA
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"] == CONFIG_DATA
    assert result["result"].unique_id == RESULT_UNIQUE_ID
    assert len(mock_setup_entry.mock_calls) == 1


async def test_config_flow_failure_adding_non_unique_account(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_touchlinesl_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the config flow fails when user tries to add duplicate accounts."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], CONFIG_DATA
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
