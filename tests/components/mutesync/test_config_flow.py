"""Test the mütesync config flow."""

from unittest.mock import patch

import aiohttp
import pytest

from menuai import config_entries
from menuai.components.mutesync.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "mutesync.authenticate",
            return_value="bla",
        ),
        patch(
            "menuai.components.mutesync.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "token": "bla",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (Exception, "unknown"),
        (aiohttp.ClientResponseError(None, None, status=403), "invalid_auth"),
        (aiohttp.ClientResponseError(None, None, status=500), "cannot_connect"),
        (TimeoutError, "cannot_connect"),
    ],
)
async def test_form_error(
    side_effect: Exception, error: str, menuai: menuai
) -> None:
    """Test we handle error situations."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "mutesync.authenticate",
        side_effect=side_effect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}
