"""Test the Linear Garage Door config flow."""

from unittest.mock import AsyncMock, patch

from linear_garage_door.errors import InvalidLoginError
import pytest

from menuai.components.linear_garage_door.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(
    menuai: menuai, mock_linear: AsyncMock, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch(
        "uuid.uuid4",
        return_value="test-uuid",
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "test-email",
                CONF_PASSWORD: "test-password",
            },
        )
        await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"site": "test-site-id"}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-site-name"
    assert result["data"] == {
        CONF_EMAIL: "test-email",
        CONF_PASSWORD: "test-password",
        "site_id": "test-site-id",
        "device_id": "test-uuid",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauth(
    menuai: menuai,
    mock_linear: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reauthentication."""
    mock_config_entry.add_to_menuai(menuai)
    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "uuid.uuid4",
        return_value="test-uuid",
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "new-email",
                CONF_PASSWORD: "new-password",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert mock_config_entry.data == {
        CONF_EMAIL: "new-email",
        CONF_PASSWORD: "new-password",
        "site_id": "test-site-id",
        "device_id": "test-uuid",
    }


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [(InvalidLoginError, "invalid_auth"), (Exception, "unknown")],
)
async def test_form_exceptions(
    menuai: menuai,
    mock_linear: AsyncMock,
    mock_setup_entry: AsyncMock,
    side_effect: Exception,
    expected_error: str,
) -> None:
    """Test we handle invalid auth."""
    mock_linear.login.side_effect = side_effect
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "test-email",
            CONF_PASSWORD: "test-password",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}
    mock_linear.login.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "test-email",
            CONF_PASSWORD: "test-password",
        },
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"site": "test-site-id"}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
