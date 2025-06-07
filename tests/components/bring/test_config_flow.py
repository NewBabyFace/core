"""Test the Bring! config flow."""

from unittest.mock import AsyncMock

from bring_api import BringAuthException, BringParseException, BringRequestException
import pytest

from menuai.components.bring.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import EMAIL, PASSWORD

from tests.common import MockConfigEntry

MOCK_DATA_STEP = {
    CONF_EMAIL: EMAIL,
    CONF_PASSWORD: PASSWORD,
}


async def test_form(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_bring_client: AsyncMock
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_STEP,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bring"
    assert result["data"] == MOCK_DATA_STEP
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (BringRequestException(), "cannot_connect"),
        (BringAuthException(), "invalid_auth"),
        (BringParseException(), "unknown"),
        (IndexError(), "unknown"),
    ],
)
async def test_flow_user_init_data_unknown_error_and_recover(
    menuai: menuai, mock_bring_client: AsyncMock, raise_error, text_error
) -> None:
    """Test unknown errors."""
    mock_bring_client.login.side_effect = raise_error

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_STEP,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == text_error

    # Recover
    mock_bring_client.login.side_effect = None
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_STEP,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].title == "Bring"

    assert result["data"] == MOCK_DATA_STEP


async def test_flow_user_init_data_already_configured(
    menuai: menuai,
    mock_bring_client: AsyncMock,
    bring_config_entry: MockConfigEntry,
) -> None:
    """Test we abort user data set when entry is already configured."""

    bring_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_STEP,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_reauth(
    menuai: menuai,
    mock_bring_client: AsyncMock,
    bring_config_entry: MockConfigEntry,
) -> None:
    """Test reauth flow."""

    bring_config_entry.add_to_menuai(menuai)

    result = await bring_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert bring_config_entry.data == {
        CONF_EMAIL: "new-email",
        CONF_PASSWORD: "new-password",
    }
    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (BringRequestException(), "cannot_connect"),
        (BringAuthException(), "invalid_auth"),
        (BringParseException(), "unknown"),
        (IndexError(), "unknown"),
    ],
)
async def test_flow_reauth_error_and_recover(
    menuai: menuai,
    mock_bring_client: AsyncMock,
    bring_config_entry: MockConfigEntry,
    raise_error,
    text_error,
) -> None:
    """Test reauth flow."""

    bring_config_entry.add_to_menuai(menuai)

    result = await bring_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_bring_client.login.side_effect = raise_error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    mock_bring_client.login.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert len(menuai.config_entries.async_entries()) == 1


async def test_flow_reauth_unique_id_mismatch(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test we abort reauth if unique id mismatch."""

    mock_bring_client.uuid = "11111111-11111111-11111111-11111111"

    bring_config_entry.add_to_menuai(menuai)

    result = await bring_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"


@pytest.mark.usefixtures("mock_bring_client")
async def test_flow_reconfigure(
    menuai: menuai, bring_config_entry: MockConfigEntry
) -> None:
    """Test reconfigure flow."""
    bring_config_entry.add_to_menuai(menuai)
    result = await bring_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert bring_config_entry.data[CONF_EMAIL] == "new-email"
    assert bring_config_entry.data[CONF_PASSWORD] == "new-password"

    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (BringRequestException(), "cannot_connect"),
        (BringAuthException(), "invalid_auth"),
        (BringParseException(), "unknown"),
        (IndexError(), "unknown"),
    ],
)
async def test_flow_reconfigure_errors(
    menuai: menuai,
    mock_bring_client: AsyncMock,
    bring_config_entry: MockConfigEntry,
    raise_error: Exception,
    text_error: str,
) -> None:
    """Test reconfigure flow errors."""
    bring_config_entry.add_to_menuai(menuai)
    result = await bring_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    mock_bring_client.login.side_effect = raise_error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    mock_bring_client.login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert bring_config_entry.data[CONF_EMAIL] == "new-email"
    assert bring_config_entry.data[CONF_PASSWORD] == "new-password"

    assert len(menuai.config_entries.async_entries()) == 1


async def test_flow_reconfigure_unique_id_mismatch(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test we abort reconfigure if unique id mismatch."""

    mock_bring_client.uuid = "11111111-11111111-11111111-11111111"

    bring_config_entry.add_to_menuai(menuai)

    result = await bring_config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "new-email", CONF_PASSWORD: "new-password"},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
