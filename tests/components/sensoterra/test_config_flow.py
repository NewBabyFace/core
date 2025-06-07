"""Test the Sensoterra config flow."""

from unittest.mock import AsyncMock

from jwt import DecodeError
import pytest
from sensoterra.customerapi import InvalidAuth as StInvalidAuth, Timeout as StTimeout

from menuai.components.sensoterra.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import API_EMAIL, API_PASSWORD, API_TOKEN, menuai_UUID

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai,
    mock_customer_api_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we can finish a config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    menuai.data["core.uuid"] = menuai_UUID
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: API_EMAIL,
            CONF_PASSWORD: API_PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == API_EMAIL
    assert result["data"] == {
        CONF_TOKEN: API_TOKEN,
        CONF_EMAIL: API_EMAIL,
    }

    assert len(mock_customer_api_client.mock_calls) == 1


async def test_form_unique_id(
    menuai: menuai, mock_customer_api_client: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    menuai.data["core.uuid"] = menuai_UUID

    entry = MockConfigEntry(unique_id="39", domain=DOMAIN)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: API_EMAIL,
            CONF_PASSWORD: API_PASSWORD,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    assert len(mock_customer_api_client.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (StTimeout, "cannot_connect"),
        (StInvalidAuth("Invalid credentials"), "invalid_auth"),
        (DecodeError("Bad API token"), "invalid_access_token"),
    ],
)
async def test_form_exceptions(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_customer_api_client: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle config form exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    menuai.data["core.uuid"] = menuai_UUID

    mock_customer_api_client.get_token.side_effect = exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: API_EMAIL,
            CONF_PASSWORD: API_PASSWORD,
        },
    )
    assert result["errors"] == {"base": error}
    assert result["type"] is FlowResultType.FORM

    mock_customer_api_client.get_token.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: API_EMAIL,
            CONF_PASSWORD: API_PASSWORD,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == API_EMAIL
    assert result["data"] == {
        CONF_TOKEN: API_TOKEN,
        CONF_EMAIL: API_EMAIL,
    }
    assert len(mock_customer_api_client.mock_calls) == 2
