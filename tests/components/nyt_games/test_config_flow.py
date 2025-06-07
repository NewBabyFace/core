"""Tests for the NYT Games config flow."""

from unittest.mock import AsyncMock

from nyt_games import NYTGamesAuthenticationError, NYTGamesError
import pytest

from menuai.components.nyt_games.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai,
    mock_nyt_games_client: AsyncMock,
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
        {CONF_TOKEN: "token"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "NYT Games"
    assert result["data"] == {CONF_TOKEN: "token"}
    assert result["result"].unique_id == "218886794"


async def test_stripping_token(
    menuai: menuai,
    mock_nyt_games_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test stripping token."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: " token "},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_TOKEN: "token"}


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (NYTGamesAuthenticationError, "invalid_auth"),
        (NYTGamesError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_flow_errors(
    menuai: menuai,
    mock_nyt_games_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test flow errors."""
    mock_nyt_games_client.get_user_id.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "token"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_nyt_games_client.get_user_id.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "token"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate(
    menuai: menuai,
    mock_nyt_games_client: AsyncMock,
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
        {CONF_TOKEN: "token"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
