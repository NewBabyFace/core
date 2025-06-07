"""Tests for the config flow."""

from unittest.mock import AsyncMock, MagicMock

from ohme import ApiException, AuthException
import pytest

from menuai.components.ohme.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_config_flow_success(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_client: MagicMock
) -> None:
    """Test config flow."""

    # Initial form load
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    # Successful login
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@example.com", CONF_PASSWORD: "hunter2"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "hunter2",
    }


@pytest.mark.parametrize(
    ("test_exception", "expected_error"),
    [(AuthException, "invalid_auth"), (ApiException, "unknown")],
)
async def test_config_flow_fail(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_client: MagicMock,
    test_exception: Exception,
    expected_error: str,
) -> None:
    """Test config flow errors."""

    # Initial form load
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    # Failed login
    mock_client.async_login.side_effect = test_exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@example.com", CONF_PASSWORD: "hunter1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    # End with CREATE_ENTRY
    mock_client.async_login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: "test@example.com", CONF_PASSWORD: "hunter1"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "hunter1",
    }


async def test_already_configured(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Ensure we can't add the same account twice."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "hunter3",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_form(menuai: menuai, mock_client: MagicMock) -> None:
    """Test reauth form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "hunter1",
        },
    )
    entry.add_to_menuai(menuai)
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    assert not result["errors"]
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter2"},
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("test_exception", "expected_error"),
    [(AuthException, "invalid_auth"), (ApiException, "unknown")],
)
async def test_reauth_fail(
    menuai: menuai,
    mock_client: MagicMock,
    test_exception: Exception,
    expected_error: str,
) -> None:
    """Test reauth errors."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "hunter1",
        },
    )
    entry.add_to_menuai(menuai)

    # Initial form load
    result = await entry.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    # Failed login
    mock_client.async_login.side_effect = test_exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    # End with success
    mock_client.async_login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter2"},
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reconfigure_form(menuai: menuai, mock_client: MagicMock) -> None:
    """Test reconfigure form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "hunter1",
        },
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter2"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


@pytest.mark.parametrize(
    ("test_exception", "expected_error"),
    [(AuthException, "invalid_auth"), (ApiException, "unknown")],
)
async def test_reconfigure_fail(
    menuai: menuai,
    mock_client: MagicMock,
    test_exception: Exception,
    expected_error: str,
) -> None:
    """Test reconfigure errors."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "hunter1",
        },
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )

    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    # Simulate failed login attempt
    mock_client.async_login.side_effect = test_exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    # Retry with a successful login
    mock_client.async_login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PASSWORD: "hunter2"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
