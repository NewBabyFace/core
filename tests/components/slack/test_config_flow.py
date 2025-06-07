"""Test Slack config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.slack.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import CONF_DATA, CONF_INPUT, TEAM_NAME, create_entry, mock_connection

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_flow_user(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test user initialized flow."""
    mock_connection(aioclient_mock)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONF_INPUT,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEAM_NAME
    assert result["data"] == CONF_DATA


async def test_flow_user_already_configured(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test user initialized flow with duplicate server."""
    create_entry(menuai)
    mock_connection(aioclient_mock)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONF_INPUT,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_user_invalid_auth(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test user initialized flow with invalid token."""
    mock_connection(aioclient_mock, "invalid_auth")
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=CONF_DATA,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_flow_user_cannot_connect(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test user initialized flow with unreachable server."""
    mock_connection(aioclient_mock, "cannot_connect")
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=CONF_DATA,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_unknown_error(menuai: menuai) -> None:
    """Test user initialized flow with unreachable server."""
    with patch(
        "menuai.components.slack.config_flow.AsyncWebClient.auth_test"
    ) as mock:
        mock.side_effect = Exception
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=CONF_DATA,
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}
