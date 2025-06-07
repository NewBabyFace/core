"""Test the CalDAV config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

from caldav.lib.error import AuthorizationError, DAVError
import pytest
import requests

from menuai import config_entries
from menuai.components.caldav.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import TEST_PASSWORD, TEST_URL, TEST_USERNAME

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        f"menuai.components.{DOMAIN}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test successful config flow setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_VERIFY_SSL: False,
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == TEST_USERNAME
    assert result2.get("data") == {
        CONF_URL: TEST_URL,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_VERIFY_SSL: False,
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (Exception(), "unknown"),
        (requests.ConnectionError(), "cannot_connect"),
        (DAVError(), "cannot_connect"),
        (AuthorizationError(reason="Unauthorized"), "invalid_auth"),
        (AuthorizationError(reason="Other"), "cannot_connect"),
    ],
)
async def test_caldav_client_error(
    menuai: menuai,
    side_effect: Exception,
    expected_error: str,
    dav_client: Mock,
) -> None:
    """Test CalDav client errors during configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    dav_client.return_value.principal.side_effect = side_effect

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("errors") == {"base": expected_error}


async def test_reauth_success(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test reauthentication configuration flow."""

    config_entry.add_to_menuai(menuai)

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "password-2",
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "reauth_successful"

    # Verify updated configuration entry
    assert dict(config_entry.data) == {
        CONF_URL: "https://example.com/url-1",
        CONF_USERNAME: "username-1",
        CONF_PASSWORD: "password-2",
        CONF_VERIFY_SSL: True,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauth_failure(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    config_entry: MockConfigEntry,
    dav_client: Mock,
) -> None:
    """Test a failure during reauthentication configuration flow."""

    config_entry.add_to_menuai(menuai)

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    dav_client.return_value.principal.side_effect = DAVError

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "password-2",
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("errors") == {"base": "cannot_connect"}

    # Complete the form and it succeeds this time
    dav_client.return_value.principal.side_effect = None
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PASSWORD: "password-3",
        },
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "reauth_successful"

    # Verify updated configuration entry
    assert dict(config_entry.data) == {
        CONF_URL: "https://example.com/url-1",
        CONF_USERNAME: "username-1",
        CONF_PASSWORD: "password-3",
        CONF_VERIFY_SSL: True,
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("user_input"),
    [
        {
            CONF_URL: f"{TEST_URL}/different-path",
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: f"{TEST_USERNAME}-different-user",
            CONF_PASSWORD: TEST_PASSWORD,
        },
    ],
)
async def test_multiple_config_entries(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    config_entry: MockConfigEntry,
    user_input: dict[str, str],
) -> None:
    """Test multiple configuration entries with unique settings."""

    config_entry.add_to_menuai(menuai)
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == user_input[CONF_USERNAME]
    assert result2.get("data") == {
        **user_input,
        CONF_VERIFY_SSL: True,
    }
    assert len(mock_setup_entry.mock_calls) == 2
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2


@pytest.mark.parametrize(
    ("user_input"),
    [
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
        {
            CONF_URL: TEST_URL,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: f"{TEST_PASSWORD}-different",
        },
    ],
)
async def test_duplicate_config_entries(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    config_entry: MockConfigEntry,
    user_input: dict[str, str],
) -> None:
    """Test multiple configuration entries with the same settings."""

    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "already_configured"
