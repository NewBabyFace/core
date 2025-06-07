"""Test the Dexcom config flow."""

from unittest.mock import patch

from pydexcom import AccountError, SessionError

from menuai import config_entries
from menuai.components.dexcom.const import DOMAIN
from menuai.const import CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import CONFIG


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.dexcom.config_flow.Dexcom.create_session",
            return_value="test_session_id",
        ),
        patch(
            "menuai.components.dexcom.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIG[CONF_USERNAME]
    assert result2["data"] == CONFIG
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_account_error(menuai: menuai) -> None:
    """Test we handle account error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.dexcom.config_flow.Dexcom",
        side_effect=AccountError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_session_error(menuai: menuai) -> None:
    """Test we handle session error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.dexcom.config_flow.Dexcom",
        side_effect=SessionError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(menuai: menuai) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.dexcom.config_flow.Dexcom",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
