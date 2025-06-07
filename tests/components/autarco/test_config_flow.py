"""Test the Autarco config flow."""

from unittest.mock import AsyncMock, patch

from autarco import AutarcoAuthenticationError, AutarcoConnectionError
import pytest

from menuai.components.autarco.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(
    menuai: menuai,
    mock_autarco_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert not result.get("errors")

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: "test@autarco.com", CONF_PASSWORD: "test-password"},
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "test@autarco.com"
    assert result.get("data") == {
        CONF_EMAIL: "test@autarco.com",
        CONF_PASSWORD: "test-password",
    }
    assert len(mock_autarco_client.get_account.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_autarco_client: AsyncMock,
) -> None:
    """Test abort when setting up duplicate entry."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert not result.get("errors")

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: "test@autarco.com", CONF_PASSWORD: "test-password"},
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AutarcoConnectionError, "cannot_connect"),
        (AutarcoAuthenticationError, "invalid_auth"),
    ],
)
async def test_exceptions(
    menuai: menuai,
    mock_autarco_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test exceptions."""
    mock_autarco_client.get_account.side_effect = exception
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: "test@autarco.com", CONF_PASSWORD: "test-password"},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": error}

    # Recover from error
    mock_autarco_client.get_account.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: "test@autarco.com", CONF_PASSWORD: "test-password"},
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY


async def test_step_reauth(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_config_entry.add_to_menuai(menuai)
    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "reauth_confirm"

    with patch("menuai.components.autarco.config_flow.Autarco", autospec=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "new-password"},
        )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reauth_successful"

    assert len(menuai.config_entries.async_entries()) == 1
    assert mock_config_entry.data[CONF_PASSWORD] == "new-password"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AutarcoConnectionError, "cannot_connect"),
        (AutarcoAuthenticationError, "invalid_auth"),
    ],
)
async def test_step_reauth_exceptions(
    menuai: menuai,
    mock_autarco_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test exceptions in reauth flow."""
    mock_autarco_client.get_account.side_effect = exception
    mock_config_entry.add_to_menuai(menuai)
    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "new-password"},
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": error}

    # Recover from error
    mock_autarco_client.get_account.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "new-password"},
    )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reauth_successful"

    assert len(menuai.config_entries.async_entries()) == 1
    assert mock_config_entry.data[CONF_PASSWORD] == "new-password"
