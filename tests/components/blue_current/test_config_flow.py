"""Test the Blue Current config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.blue_current import DOMAIN
from menuai.components.blue_current.config_flow import (
    AlreadyConnected,
    InvalidApiToken,
    RequestLimitReached,
    WebsocketError,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test if the form is created."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {}
    assert result["type"] is FlowResultType.FORM


async def test_user(menuai: menuai) -> None:
    """Test if the api token is set."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {}
    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "menuai.components.blue_current.config_flow.Client.validate_api_token",
            return_value="1234",
        ),
        patch(
            "menuai.components.blue_current.config_flow.Client.get_email",
            return_value="test@email.com",
        ),
        patch(
            "menuai.components.blue_current.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_token": "123",
            },
        )
        await menuai.async_block_till_done()

    assert result2["title"] == "test@email.com"
    assert result2["data"] == {"api_token": "123"}
    assert result2["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (InvalidApiToken(), "invalid_token"),
        (RequestLimitReached(), "limit_reached"),
        (AlreadyConnected(), "already_connected"),
        (Exception(), "unknown"),
        (WebsocketError(), "cannot_connect"),
    ],
)
async def test_flow_fails(menuai: menuai, error: Exception, message: str) -> None:
    """Test bluecurrent api errors during configuration flow."""
    with patch(
        "menuai.components.blue_current.config_flow.Client.validate_api_token",
        side_effect=error,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={"api_token": "123"},
        )
        assert result["errors"]["base"] == message
        assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "menuai.components.blue_current.config_flow.Client.validate_api_token",
            return_value="1234",
        ),
        patch(
            "menuai.components.blue_current.config_flow.Client.get_email",
            return_value="test@email.com",
        ),
        patch(
            "menuai.components.blue_current.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_token": "123",
            },
        )
        await menuai.async_block_till_done()

        assert result2["title"] == "test@email.com"
        assert result2["data"] == {"api_token": "123"}
        assert result2["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("customer_id", "reason", "expected_api_token"),
    [
        ("1234", "reauth_successful", "1234567890"),
        ("6666", "wrong_account", "123"),
    ],
)
async def test_reauth(
    menuai: menuai,
    config_entry: MockConfigEntry,
    customer_id: str,
    reason: str,
    expected_api_token: str,
) -> None:
    """Test reauth flow."""
    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.blue_current.config_flow.Client.validate_api_token",
            return_value=customer_id,
        ),
        patch(
            "menuai.components.blue_current.config_flow.Client.get_email",
            return_value="test@email.com",
        ),
        patch(
            "menuai.components.blue_current.config_flow.Client.wait_for_charge_points",
        ),
        patch(
            "menuai.components.blue_current.Client.connect",
            lambda self, on_data, on_open: menuai.loop.create_future(),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_token": "1234567890"},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == reason
        assert config_entry.data["api_token"] == expected_api_token

        await menuai.async_block_till_done()
