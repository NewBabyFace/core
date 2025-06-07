"""Test the Aquacell config flow."""

from unittest.mock import AsyncMock

from aioaquacell import ApiException, AuthenticationFailed
import pytest

from menuai.components.aquacell.const import (
    CONF_BRAND,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import TEST_CONFIG_ENTRY, TEST_USER_INPUT

from tests.common import MockConfigEntry


async def test_config_flow_already_configured(menuai: menuai) -> None:
    """Test already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **TEST_CONFIG_ENTRY,
        },
        unique_id=TEST_CONFIG_ENTRY[CONF_EMAIL],
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_USER_INPUT,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_full_flow(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_aquacell_api: AsyncMock
) -> None:
    """Test the full config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result2["data"][CONF_EMAIL] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result2["data"][CONF_PASSWORD] == TEST_CONFIG_ENTRY[CONF_PASSWORD]
    assert result2["data"][CONF_REFRESH_TOKEN] == TEST_CONFIG_ENTRY[CONF_REFRESH_TOKEN]
    assert result2["data"][CONF_BRAND] == TEST_CONFIG_ENTRY[CONF_BRAND]
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ApiException, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (AuthenticationFailed, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_form_exceptions(
    menuai: menuai,
    exception: Exception,
    error: str,
    mock_setup_entry: AsyncMock,
    mock_aquacell_api: AsyncMock,
) -> None:
    """Test we handle form exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    mock_aquacell_api.authenticate.side_effect = exception
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}

    mock_aquacell_api.authenticate.side_effect = None

    result3 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result3["data"][CONF_EMAIL] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result3["data"][CONF_PASSWORD] == TEST_CONFIG_ENTRY[CONF_PASSWORD]
    assert result3["data"][CONF_REFRESH_TOKEN] == TEST_CONFIG_ENTRY[CONF_REFRESH_TOKEN]
    assert result3["data"][CONF_BRAND] == TEST_CONFIG_ENTRY[CONF_BRAND]
    assert len(mock_setup_entry.mock_calls) == 1
