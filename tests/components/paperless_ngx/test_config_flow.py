"""Tests for the Paperless-ngx config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock

from pypaperless.exceptions import (
    InitializationError,
    PaperlessConnectionError,
    PaperlessForbiddenError,
    PaperlessInactiveOrDeletedError,
    PaperlessInvalidTokenError,
)
import pytest

from menuai import config_entries
from menuai.components.paperless_ngx.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY, CONF_URL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import USER_INPUT_ONE, USER_INPUT_REAUTH, USER_INPUT_TWO

from tests.common import MockConfigEntry, patch


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.paperless_ngx.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_full_config_flow(menuai: menuai) -> None:
    """Test registering an integration and finishing flow works."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["flow_id"]
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT_ONE,
    )

    config_entry = result["result"]
    assert config_entry.title == USER_INPUT_ONE[CONF_URL]
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.data == USER_INPUT_ONE


async def test_full_reauth_flow(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reauth an integration and finishing flow works."""

    mock_config_entry.add_to_menuai(menuai)

    reauth_flow = await mock_config_entry.start_reauth_flow(menuai)
    assert reauth_flow["type"] is FlowResultType.FORM
    assert reauth_flow["step_id"] == "reauth_confirm"

    result_configure = await menuai.config_entries.flow.async_configure(
        reauth_flow["flow_id"], USER_INPUT_REAUTH
    )

    assert result_configure["type"] is FlowResultType.ABORT
    assert result_configure["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == USER_INPUT_REAUTH[CONF_API_KEY]


async def test_full_reconfigure_flow(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test reconfigure an integration and finishing flow works."""

    mock_config_entry.add_to_menuai(menuai)

    reconfigure_flow = await mock_config_entry.start_reconfigure_flow(menuai)
    assert reconfigure_flow["type"] is FlowResultType.FORM
    assert reconfigure_flow["step_id"] == "reconfigure"

    result_configure = await menuai.config_entries.flow.async_configure(
        reconfigure_flow["flow_id"],
        USER_INPUT_TWO,
    )

    assert result_configure["type"] is FlowResultType.ABORT
    assert result_configure["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == USER_INPUT_TWO


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PaperlessConnectionError(), {CONF_URL: "cannot_connect"}),
        (PaperlessInvalidTokenError(), {CONF_API_KEY: "invalid_api_key"}),
        (PaperlessInactiveOrDeletedError(), {CONF_API_KEY: "user_inactive_or_deleted"}),
        (PaperlessForbiddenError(), {CONF_API_KEY: "forbidden"}),
        (InitializationError(), {CONF_URL: "cannot_connect"}),
        (Exception("BOOM!"), {"base": "unknown"}),
    ],
)
async def test_config_flow_error_handling(
    menuai: menuai,
    mock_paperless: AsyncMock,
    side_effect: Exception,
    expected_error: dict[str, str],
) -> None:
    """Test user step shows correct error for various client initialization issues."""
    mock_paperless.initialize.side_effect = side_effect

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=USER_INPUT_ONE,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == expected_error

    mock_paperless.initialize.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=USER_INPUT_ONE,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USER_INPUT_ONE[CONF_URL]
    assert result["data"] == USER_INPUT_ONE


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PaperlessConnectionError(), {CONF_URL: "cannot_connect"}),
        (PaperlessInvalidTokenError(), {CONF_API_KEY: "invalid_api_key"}),
        (PaperlessInactiveOrDeletedError(), {CONF_API_KEY: "user_inactive_or_deleted"}),
        (PaperlessForbiddenError(), {CONF_API_KEY: "forbidden"}),
        (InitializationError(), {CONF_URL: "cannot_connect"}),
        (Exception("BOOM!"), {"base": "unknown"}),
    ],
)
async def test_reauth_flow_error_handling(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_paperless: AsyncMock,
    side_effect: Exception,
    expected_error: str,
) -> None:
    """Test reauth flow with various initialization errors."""

    mock_config_entry.add_to_menuai(menuai)
    mock_paperless.initialize.side_effect = side_effect

    reauth_flow = await mock_config_entry.start_reauth_flow(menuai)
    assert reauth_flow["type"] is FlowResultType.FORM
    assert reauth_flow["step_id"] == "reauth_confirm"

    result_configure = await menuai.config_entries.flow.async_configure(
        reauth_flow["flow_id"], USER_INPUT_REAUTH
    )

    await menuai.async_block_till_done()

    assert result_configure["type"] is FlowResultType.FORM
    assert result_configure["errors"] == expected_error


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (PaperlessConnectionError(), {CONF_URL: "cannot_connect"}),
        (PaperlessInvalidTokenError(), {CONF_API_KEY: "invalid_api_key"}),
        (PaperlessInactiveOrDeletedError(), {CONF_API_KEY: "user_inactive_or_deleted"}),
        (PaperlessForbiddenError(), {CONF_API_KEY: "forbidden"}),
        (InitializationError(), {CONF_URL: "cannot_connect"}),
        (Exception("BOOM!"), {"base": "unknown"}),
    ],
)
async def test_reconfigure_flow_error_handling(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_paperless: AsyncMock,
    side_effect: Exception,
    expected_error: str,
) -> None:
    """Test reconfigure flow with various initialization errors."""

    mock_config_entry.add_to_menuai(menuai)
    mock_paperless.initialize.side_effect = side_effect

    reauth_flow = await mock_config_entry.start_reconfigure_flow(menuai)
    assert reauth_flow["type"] is FlowResultType.FORM
    assert reauth_flow["step_id"] == "reconfigure"

    result_configure = await menuai.config_entries.flow.async_configure(
        reauth_flow["flow_id"],
        USER_INPUT_TWO,
    )

    await menuai.async_block_till_done()

    assert result_configure["type"] is FlowResultType.FORM
    assert result_configure["errors"] == expected_error


async def test_config_already_exists(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test we only allow a single config flow."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=USER_INPUT_ONE,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_already_exists_reconfigure(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we only allow a single config if reconfiguring an entry."""
    mock_config_entry.add_to_menuai(menuai)
    mock_config_entry_two = MockConfigEntry(
        entry_id="J87G00V55WEVTJ0CJHM0GADBH5",
        title="Paperless-ngx - Two",
        domain=DOMAIN,
        data=USER_INPUT_TWO,
    )
    mock_config_entry_two.add_to_menuai(menuai)

    reconfigure_flow = await mock_config_entry_two.start_reconfigure_flow(menuai)
    assert reconfigure_flow["type"] is FlowResultType.FORM
    assert reconfigure_flow["step_id"] == "reconfigure"

    result_configure = await menuai.config_entries.flow.async_configure(
        reconfigure_flow["flow_id"],
        USER_INPUT_ONE,
    )

    assert result_configure["type"] is FlowResultType.ABORT
    assert result_configure["reason"] == "already_configured"
