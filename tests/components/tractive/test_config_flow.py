"""Test the tractive config flow."""

from unittest.mock import patch

import aiotractive

from menuai import config_entries
from menuai.components.tractive.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

USER_INPUT = {
    "email": "test-email@example.com",
    "password": "test-password",
}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch("aiotractive.api.API.user_id", return_value="user_id"),
        patch(
            "menuai.components.tractive.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-email@example.com"
    assert result2["data"] == USER_INPUT
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=aiotractive.exceptions.UnauthorizedError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_unknown_error(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_flow_entry_already_exists(menuai: menuai) -> None:
    """Test user input for config_entry that already exists."""
    first_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    first_entry.add_to_menuai(menuai)

    with patch("aiotractive.api.API.user_id", return_value="USERID"):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=USER_INPUT
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauthentication(menuai: menuai) -> None:
    """Test Tractive reauthentication."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with (
        patch("aiotractive.api.API.user_id", return_value="USERID"),
        patch(
            "menuai.components.tractive.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauthentication_failure(menuai: menuai) -> None:
    """Test Tractive reauthentication failure."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=aiotractive.exceptions.UnauthorizedError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "invalid_auth"


async def test_reauthentication_unknown_failure(menuai: menuai) -> None:
    """Test Tractive reauthentication failure."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "unknown"


async def test_reauthentication_failure_no_existing_entry(menuai: menuai) -> None:
    """Test Tractive reauthentication with no existing entry."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch("aiotractive.api.API.user_id", return_value="USERID_DIFFERENT"):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_failed_existing"
