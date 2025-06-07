"""Test config flow for Swing2Sleep Smarla integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from menuai.components.smarla.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import MOCK_SERIAL_NUMBER, MOCK_USER_INPUT

from tests.common import MockConfigEntry


async def test_config_flow(
    menuai: menuai, mock_setup_entry, mock_connection: MagicMock
) -> None:
    """Test creating a config entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_SERIAL_NUMBER
    assert result["data"] == MOCK_USER_INPUT
    assert result["result"].unique_id == MOCK_SERIAL_NUMBER


async def test_malformed_token(
    menuai: menuai, mock_setup_entry, mock_connection: MagicMock
) -> None:
    """Test we show user form on malformed token input."""
    with patch(
        "menuai.components.smarla.config_flow.Connection", side_effect=ValueError
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "malformed_token"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_invalid_auth(
    menuai: menuai, mock_setup_entry, mock_connection: MagicMock
) -> None:
    """Test we show user form on invalid auth."""
    with patch.object(
        mock_connection, "refresh_token", new=AsyncMock(return_value=False)
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_device_exists_abort(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_connection: MagicMock
) -> None:
    """Test we abort config flow if Smarla device already configured."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=MOCK_USER_INPUT,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
