"""Test the Smart Meter Texas config flow."""

from unittest.mock import patch

from aiohttp import ClientError
import pytest
from smart_meter_texas.exceptions import (
    SmartMeterTexasAPIError,
    SmartMeterTexasAuthError,
)

from menuai import config_entries
from menuai.components.smart_meter_texas.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_LOGIN = {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch("smart_meter_texas.Client.authenticate", return_value=True),
        patch(
            "menuai.components.smart_meter_texas.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_LOGIN
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_LOGIN[CONF_USERNAME]
    assert result2["data"] == TEST_LOGIN
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "smart_meter_texas.Client.authenticate",
        side_effect=SmartMeterTexasAuthError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_LOGIN,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    "side_effect", [TimeoutError, ClientError, SmartMeterTexasAPIError]
)
async def test_form_cannot_connect(menuai: menuai, side_effect) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "smart_meter_texas.Client.authenticate",
        side_effect=side_effect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_LOGIN
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_exception(menuai: menuai) -> None:
    """Test base exception is handled."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "smart_meter_texas.Client.authenticate",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            TEST_LOGIN,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_duplicate_account(menuai: menuai) -> None:
    """Test that a duplicate account cannot be configured."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="user123",
        data={"username": "user123", "password": "password123"},
    ).add_to_menuai(menuai)

    with patch(
        "smart_meter_texas.Client.authenticate",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={"username": "user123", "password": "password123"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
