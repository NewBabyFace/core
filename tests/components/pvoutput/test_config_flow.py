"""Tests for the PVOutput config flow."""

from unittest.mock import AsyncMock, MagicMock

from pvo import PVOutputAuthenticationError, PVOutputConnectionError

from menuai.components.pvoutput.const import CONF_SYSTEM_ID, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(
    menuai: menuai,
    mock_pvoutput: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "12345"
    assert result2.get("data") == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "tadaaa",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput.system.mock_calls) == 1


async def test_full_flow_with_authentication_error(
    menuai: menuai,
    mock_pvoutput: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow with incorrect API key.

    This tests tests a full config flow, with a case the user enters an invalid
    PVOutput API key, but recovers by entering the correct one.
    """
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    mock_pvoutput.system.side_effect = PVOutputAuthenticationError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "invalid",
        },
    )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "user"
    assert result2.get("errors") == {"base": "invalid_auth"}

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(mock_pvoutput.system.mock_calls) == 1

    mock_pvoutput.system.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result3.get("type") is FlowResultType.CREATE_ENTRY
    assert result3.get("title") == "12345"
    assert result3.get("data") == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "tadaaa",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput.system.mock_calls) == 2


async def test_connection_error(menuai: menuai, mock_pvoutput: MagicMock) -> None:
    """Test API connection error."""
    mock_pvoutput.system.side_effect = PVOutputConnectionError

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "cannot_connect"}

    assert len(mock_pvoutput.system.mock_calls) == 1


async def test_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
) -> None:
    """Test we abort if the PVOutput system is already configured."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "already_configured"


async def test_reauth_flow(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the reauthentication configuration flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "reauth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "some_new_key"},
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "some_new_key",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput.system.mock_calls) == 1


async def test_reauth_with_authentication_error(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the reauthentication configuration flow with an authentication error.

    This tests tests a reauth flow, with a case the user enters an invalid
    API key, but recover by entering the correct one.
    """
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "reauth_confirm"

    mock_pvoutput.system.side_effect = PVOutputAuthenticationError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "invalid_key"},
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "reauth_confirm"
    assert result2.get("errors") == {"base": "invalid_auth"}

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(mock_pvoutput.system.mock_calls) == 1

    mock_pvoutput.system.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_API_KEY: "valid_key"},
    )
    await menuai.async_block_till_done()

    assert result3.get("type") is FlowResultType.ABORT
    assert result3.get("reason") == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "valid_key",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput.system.mock_calls) == 2


async def test_reauth_api_error(
    menuai: menuai,
    mock_pvoutput: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test API error during reauthentication."""
    mock_config_entry.add_to_menuai(menuai)

    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "reauth_confirm"

    mock_pvoutput.system.side_effect = PVOutputConnectionError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "some_new_key"},
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "reauth_confirm"
    assert result2.get("errors") == {"base": "cannot_connect"}
