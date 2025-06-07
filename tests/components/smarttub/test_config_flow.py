"""Test the smarttub config flow."""

from unittest.mock import patch

from smarttub import LoginFailed

from menuai import config_entries
from menuai.components.smarttub.const import DOMAIN
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.smarttub.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: "test-email", CONF_PASSWORD: "test-password"},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "test-email"
        assert result["data"] == {
            CONF_EMAIL: "test-email",
            CONF_PASSWORD: "test-password",
        }
        await menuai.async_block_till_done()
        mock_setup_entry.assert_called_once()


async def test_form_invalid_auth(menuai: menuai, smarttub_api) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    smarttub_api.login.side_effect = LoginFailed

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test-email", CONF_PASSWORD: "test-password"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_success(menuai: menuai, smarttub_api, account) -> None:
    """Test reauthentication flow."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test-email", CONF_PASSWORD: "test-password"},
        unique_id=account.id,
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: "test-email3", CONF_PASSWORD: "test-password3"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data[CONF_EMAIL] == "test-email3"
    assert mock_entry.data[CONF_PASSWORD] == "test-password3"


async def test_reauth_wrong_account(menuai: menuai, smarttub_api, account) -> None:
    """Test reauthentication flow if the user enters credentials for a different already-configured account."""
    mock_entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test-email1", CONF_PASSWORD: "test-password1"},
        unique_id=account.id,
    )
    mock_entry1.add_to_menuai(menuai)

    mock_entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test-email2", CONF_PASSWORD: "test-password2"},
        unique_id="mockaccount2",
    )
    mock_entry2.add_to_menuai(menuai)

    # we try to reauth account #2, and the user successfully authenticates to account #1
    account.id = mock_entry1.unique_id
    result = await mock_entry2.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: "test-email1", CONF_PASSWORD: "test-password1"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
