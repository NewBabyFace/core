"""Test the Model Context Protocol Server config flow."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from menuai import config_entries
from menuai.components.mcp_server.const import DOMAIN
from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.mark.parametrize(
    "params",
    [
        {},
        {CONF_LLM_menuai_API: "assist"},
    ],
)
async def test_form(
    menuai: menuai, mock_setup_entry: AsyncMock, params: dict[str, Any]
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        params,
    )
    await menuai.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Assist"
    assert len(mock_setup_entry.mock_calls) == 1
    assert result["data"] == {CONF_LLM_menuai_API: "assist"}
