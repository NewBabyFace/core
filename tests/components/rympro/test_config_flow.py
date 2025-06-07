"""Test the Read Your Meter Pro config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.rympro.config_flow import (
    CannotConnectError,
    UnauthorizedError,
)
from menuai.components.rympro.const import DOMAIN
from menuai.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, CONF_UNIQUE_ID
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_DATA = {
    CONF_EMAIL: "test-email",
    CONF_PASSWORD: "test-password",
    CONF_TOKEN: "test-token",
    CONF_UNIQUE_ID: "test-account-number",
}


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Create a mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_DATA,
        unique_id=TEST_DATA[CONF_UNIQUE_ID],
    )
    config_entry.add_to_menuai(menuai)
    return config_entry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.rympro.config_flow.RymPro.login",
            return_value="test-token",
        ),
        patch(
            "menuai.components.rympro.config_flow.RymPro.account_info",
            return_value={"accountNumber": TEST_DATA[CONF_UNIQUE_ID]},
        ),
        patch(
            "menuai.components.rympro.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: TEST_DATA[CONF_PASSWORD],
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_DATA[CONF_EMAIL]
    assert result2["data"] == TEST_DATA
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (UnauthorizedError, "invalid_auth"),
        (CannotConnectError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_login_error(menuai: menuai, exception, error) -> None:
    """Test we handle config flow errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "menuai.components.rympro.config_flow.RymPro.login",
        side_effect=exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: TEST_DATA[CONF_PASSWORD],
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}

    with (
        patch(
            "menuai.components.rympro.config_flow.RymPro.login",
            return_value="test-token",
        ),
        patch(
            "menuai.components.rympro.config_flow.RymPro.account_info",
            return_value={"accountNumber": TEST_DATA[CONF_UNIQUE_ID]},
        ),
        patch(
            "menuai.components.rympro.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: TEST_DATA[CONF_PASSWORD],
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_DATA[CONF_EMAIL]
    assert result3["data"] == TEST_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_already_exists(menuai: menuai, config_entry) -> None:
    """Test that a flow with an existing account aborts."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.rympro.config_flow.RymPro.login",
            return_value="test-token",
        ),
        patch(
            "menuai.components.rympro.config_flow.RymPro.account_info",
            return_value={"accountNumber": TEST_DATA[CONF_UNIQUE_ID]},
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: TEST_DATA[CONF_PASSWORD],
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_form_reauth(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test reauthentication."""

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.rympro.config_flow.RymPro.login",
            return_value="test-token",
        ),
        patch(
            "menuai.components.rympro.config_flow.RymPro.account_info",
            return_value={"accountNumber": TEST_DATA[CONF_UNIQUE_ID]},
        ),
        patch(
            "menuai.components.rympro.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: "new_password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new_password"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_reauth_with_new_account(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test reauthentication with new account."""

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.rympro.config_flow.RymPro.login",
            return_value="test-token",
        ),
        patch(
            "menuai.components.rympro.config_flow.RymPro.account_info",
            return_value={"accountNumber": "new-account-number"},
        ),
        patch(
            "menuai.components.rympro.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_DATA[CONF_EMAIL],
                CONF_PASSWORD: TEST_DATA[CONF_PASSWORD],
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert config_entry.data[CONF_UNIQUE_ID] == "new-account-number"
    assert config_entry.unique_id == "new-account-number"
    assert len(mock_setup_entry.mock_calls) == 1
