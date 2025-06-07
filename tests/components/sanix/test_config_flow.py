"""Define tests for the Sanix config flow."""

from unittest.mock import MagicMock

import pytest
from sanix.exceptions import SanixException, SanixInvalidAuthException

from menuai.components.sanix.const import (
    CONF_SERIAL_NUMBER,
    DOMAIN,
    MANUFACTURER,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

CONFIG = {CONF_SERIAL_NUMBER: "1810088", CONF_TOKEN: "75868dcf8ea4c64e2063f6c4e70132d2"}


async def test_create_entry(
    menuai: menuai, mock_sanix: MagicMock, mock_setup_entry
) -> None:
    """Test that the user step works."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MANUFACTURER
    assert result["data"] == {
        CONF_SERIAL_NUMBER: "1810088",
        CONF_TOKEN: "75868dcf8ea4c64e2063f6c4e70132d2",
    }

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (SanixInvalidAuthException("Invalid auth"), "invalid_auth"),
        (SanixException("Something went wrong"), "unknown"),
    ],
)
async def test_form_exceptions(
    menuai: menuai,
    exception: Exception,
    error: str,
    mock_sanix: MagicMock,
    mock_setup_entry,
) -> None:
    """Test Form exceptions."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    mock_sanix.return_value.fetch_data.side_effect = exception
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG,
    )

    mock_sanix.return_value.fetch_data.side_effect = None

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sanix"
    assert result["data"] == {
        CONF_SERIAL_NUMBER: "1810088",
        CONF_TOKEN: "75868dcf8ea4c64e2063f6c4e70132d2",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_error(
    menuai: menuai, mock_sanix: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test that errors are shown when duplicates are added."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        CONFIG,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
