"""Test the Ridwell config flow."""

from unittest.mock import AsyncMock, patch

from aioridwell.errors import InvalidCredentialsError, RidwellError
import pytest

from menuai import config_entries
from menuai.components.ridwell.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import TEST_PASSWORD, TEST_USERNAME

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("get_client_response", "errors"),
    [
        (AsyncMock(side_effect=InvalidCredentialsError), {"base": "invalid_auth"}),
        (AsyncMock(side_effect=RidwellError), {"base": "unknown"}),
    ],
)
async def test_create_entry(
    menuai: menuai, config, errors, get_client_response, mock_aioridwell
) -> None:
    """Test creating an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test errors that can arise:
    with patch(
        "menuai.components.ridwell.config_flow.async_get_client",
        get_client_response,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=config
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == errors

    # Test that we can recover and finish the flow after errors occur:
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USERNAME
    assert result["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }


async def test_duplicate_error(menuai: menuai, config, setup_config_entry) -> None:
    """Test that errors are shown when duplicate entries are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_reauth(
    menuai: menuai, config, config_entry: MockConfigEntry, setup_config_entry
) -> None:
    """Test a full reauth flow."""
    result = await config_entry.start_reauth_flow(menuai)
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "new_password"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(menuai.config_entries.async_entries()) == 1
