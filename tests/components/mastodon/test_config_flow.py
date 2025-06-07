"""Tests for the Mastodon config flow."""

from unittest.mock import AsyncMock

from mastodon.Mastodon import MastodonNetworkError, MastodonUnauthorizedError
import pytest

from menuai.components.mastodon.const import CONF_BASE_URL, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ACCESS_TOKEN, CONF_CLIENT_ID, CONF_CLIENT_SECRET
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
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
            CONF_BASE_URL: "https://mastodon.social",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "@trwnh@mastodon.social"
    assert result["data"] == {
        CONF_BASE_URL: "https://mastodon.social",
        CONF_CLIENT_ID: "client_id",
        CONF_CLIENT_SECRET: "client_secret",
        CONF_ACCESS_TOKEN: "access_token",
    }
    assert result["result"].unique_id == "trwnh_mastodon_social"


async def test_full_flow_with_path(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test full flow, where a path is accidentally specified."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "https://mastodon.social/home",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "@trwnh@mastodon.social"
    assert result["data"] == {
        CONF_BASE_URL: "https://mastodon.social",
        CONF_CLIENT_ID: "client_id",
        CONF_CLIENT_SECRET: "client_secret",
        CONF_ACCESS_TOKEN: "access_token",
    }
    assert result["result"].unique_id == "trwnh_mastodon_social"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (MastodonNetworkError, "network_error"),
        (MastodonUnauthorizedError, "unauthorized_error"),
        (Exception, "unknown"),
    ],
)
async def test_flow_errors(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test flow errors."""
    mock_mastodon_client.account_verify_credentials.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "https://mastodon.social",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_mastodon_client.account_verify_credentials.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "https://mastodon.social",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
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
            CONF_BASE_URL: "https://mastodon.social",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
