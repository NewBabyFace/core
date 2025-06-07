"""Test the habitica config flow."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from menuai.components.habitica.const import (
    CONF_API_USER,
    DEFAULT_URL,
    DOMAIN,
    SECTION_DANGER_ZONE,
    SECTION_REAUTH_API_KEY,
    SECTION_REAUTH_LOGIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import ERROR_BAD_REQUEST, ERROR_NOT_AUTHORIZED

from tests.common import MockConfigEntry

TEST_API_USER = "a380546a-94be-4b8e-8a0b-23e0d5c03303"
TEST_API_KEY = "cd0e5985-17de-4b4f-849e-5d506c5e4382"


MOCK_DATA_LOGIN_STEP = {
    CONF_USERNAME: "test-email@example.com",
    CONF_PASSWORD: "test-password",
}
MOCK_DATA_ADVANCED_STEP = {
    CONF_API_USER: TEST_API_USER,
    CONF_API_KEY: TEST_API_KEY,
    CONF_URL: DEFAULT_URL,
    CONF_VERIFY_SSL: True,
}

USER_INPUT_REAUTH_LOGIN = {
    SECTION_REAUTH_LOGIN: {
        CONF_USERNAME: "new-email",
        CONF_PASSWORD: "new-password",
    },
    SECTION_REAUTH_API_KEY: {},
}
USER_INPUT_REAUTH_API_KEY = {
    SECTION_REAUTH_LOGIN: {},
    SECTION_REAUTH_API_KEY: {CONF_API_KEY: "cd0e5985-17de-4b4f-849e-5d506c5e4382"},
}
USER_INPUT_RECONFIGURE = {
    CONF_API_KEY: "cd0e5985-17de-4b4f-849e-5d506c5e4382",
    SECTION_DANGER_ZONE: {
        CONF_URL: DEFAULT_URL,
        CONF_VERIFY_SSL: True,
    },
}


@pytest.mark.usefixtures("habitica")
async def test_form_login(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the login form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert "login" in result["menu_options"]
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "login"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "login"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_LOGIN_STEP,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"
    assert result["data"] == {
        CONF_API_USER: TEST_API_USER,
        CONF_API_KEY: TEST_API_KEY,
        CONF_URL: DEFAULT_URL,
        CONF_NAME: "test-user",
        CONF_VERIFY_SSL: True,
    }
    assert result["result"].unique_id == TEST_API_USER

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (ERROR_BAD_REQUEST, "cannot_connect"),
        (ERROR_NOT_AUTHORIZED, "invalid_auth"),
        (IndexError(), "unknown"),
    ],
)
async def test_form_login_errors(
    menuai: menuai, habitica: AsyncMock, raise_error, text_error
) -> None:
    """Test we handle invalid credentials error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "login"},
    )

    habitica.login.side_effect = raise_error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_LOGIN_STEP,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    # recover from errors
    habitica.login.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_LOGIN_STEP,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"
    assert result["data"] == {
        CONF_API_USER: TEST_API_USER,
        CONF_API_KEY: TEST_API_KEY,
        CONF_URL: DEFAULT_URL,
        CONF_NAME: "test-user",
        CONF_VERIFY_SSL: True,
    }
    assert result["result"].unique_id == TEST_API_USER


@pytest.mark.usefixtures("habitica")
async def test_form_already_configured(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test we abort form login when entry is already configured."""

    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "login"},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_LOGIN_STEP,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("habitica")
async def test_form_advanced(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert "advanced" in result["menu_options"]
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "advanced"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "advanced"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_ADVANCED_STEP,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"
    assert result["data"] == {
        CONF_API_USER: TEST_API_USER,
        CONF_API_KEY: TEST_API_KEY,
        CONF_URL: DEFAULT_URL,
        CONF_NAME: "test-user",
        CONF_VERIFY_SSL: True,
    }
    assert result["result"].unique_id == TEST_API_USER

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (ERROR_BAD_REQUEST, "cannot_connect"),
        (ERROR_NOT_AUTHORIZED, "invalid_auth"),
        (IndexError(), "unknown"),
    ],
)
async def test_form_advanced_errors(
    menuai: menuai, habitica: AsyncMock, raise_error, text_error
) -> None:
    """Test we handle invalid credentials error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "advanced"},
    )

    habitica.get_user.side_effect = raise_error

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_ADVANCED_STEP,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    # recover from errors
    habitica.get_user.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_ADVANCED_STEP,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"
    assert result["data"] == {
        CONF_API_USER: TEST_API_USER,
        CONF_API_KEY: TEST_API_KEY,
        CONF_URL: DEFAULT_URL,
        CONF_NAME: "test-user",
        CONF_VERIFY_SSL: True,
    }
    assert result["result"].unique_id == TEST_API_USER


@pytest.mark.usefixtures("habitica")
async def test_form_advanced_already_configured(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test we abort user data set when entry is already configured."""

    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "advanced"},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_ADVANCED_STEP,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "user_input",
    [
        (USER_INPUT_REAUTH_LOGIN),
        (USER_INPUT_REAUTH_API_KEY),
    ],
    ids=["reauth with login details", "rauth with api key"],
)
@pytest.mark.usefixtures("habitica")
async def test_flow_reauth(
    menuai: menuai, config_entry: MockConfigEntry, user_input: dict[str, Any]
) -> None:
    """Test reauth flow."""
    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_API_KEY] == "cd0e5985-17de-4b4f-849e-5d506c5e4382"

    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.parametrize(
    ("raise_error", "user_input", "text_error"),
    [
        (
            ERROR_BAD_REQUEST,
            USER_INPUT_REAUTH_LOGIN,
            "cannot_connect",
        ),
        (
            ERROR_NOT_AUTHORIZED,
            USER_INPUT_REAUTH_LOGIN,
            "invalid_auth",
        ),
        (IndexError(), USER_INPUT_REAUTH_LOGIN, "unknown"),
        (
            ERROR_BAD_REQUEST,
            USER_INPUT_REAUTH_API_KEY,
            "cannot_connect",
        ),
        (
            ERROR_NOT_AUTHORIZED,
            USER_INPUT_REAUTH_API_KEY,
            "invalid_auth",
        ),
        (IndexError(), USER_INPUT_REAUTH_API_KEY, "unknown"),
        (
            None,
            {SECTION_REAUTH_LOGIN: {}, SECTION_REAUTH_API_KEY: {}},
            "invalid_credentials",
        ),
    ],
    ids=[
        "login cannot_connect",
        "login invalid_auth",
        "login unknown",
        "api_key cannot_connect",
        "api_key invalid_auth",
        "api_key unknown",
        "invalid_credentials",
    ],
)
async def test_flow_reauth_errors(
    menuai: menuai,
    habitica: AsyncMock,
    config_entry: MockConfigEntry,
    raise_error: Exception,
    user_input: dict[str, Any],
    text_error: str,
) -> None:
    """Test reauth flow with invalid credentials."""
    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    habitica.get_user.side_effect = raise_error
    habitica.login.side_effect = raise_error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    habitica.get_user.side_effect = None
    habitica.login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=USER_INPUT_REAUTH_API_KEY,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_API_KEY] == "cd0e5985-17de-4b4f-849e-5d506c5e4382"

    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.usefixtures("habitica")
async def test_flow_reauth_unique_id_mismatch(menuai: menuai) -> None:
    """Test reauth flow."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="test-user",
        data={
            CONF_URL: DEFAULT_URL,
            CONF_API_USER: "371fcad5-0f9c-4211-931c-034a5d2a6213",
            CONF_API_KEY: "cd0e5985-17de-4b4f-849e-5d506c5e4382",
        },
        unique_id="371fcad5-0f9c-4211-931c-034a5d2a6213",
    )

    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT_REAUTH_LOGIN,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"

    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.usefixtures("habitica")
async def test_flow_reconfigure(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test reconfigure flow."""
    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT_RECONFIGURE,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_API_KEY] == "cd0e5985-17de-4b4f-849e-5d506c5e4382"
    assert config_entry.data[CONF_URL] == DEFAULT_URL
    assert config_entry.data[CONF_VERIFY_SSL] is True

    assert len(menuai.config_entries.async_entries()) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (ERROR_NOT_AUTHORIZED, "invalid_auth"),
        (ERROR_BAD_REQUEST, "cannot_connect"),
        (KeyError, "unknown"),
    ],
)
async def test_flow_reconfigure_errors(
    menuai: menuai,
    habitica: AsyncMock,
    config_entry: MockConfigEntry,
    raise_error: Exception,
    text_error: str,
) -> None:
    """Test reconfigure flow errors."""
    config_entry.add_to_menuai(menuai)
    result = await config_entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    habitica.get_user.side_effect = raise_error
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT_RECONFIGURE,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": text_error}

    habitica.get_user.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=USER_INPUT_RECONFIGURE,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_API_KEY] == "cd0e5985-17de-4b4f-849e-5d506c5e4382"
    assert config_entry.data[CONF_URL] == DEFAULT_URL
    assert config_entry.data[CONF_VERIFY_SSL] is True

    assert len(menuai.config_entries.async_entries()) == 1
