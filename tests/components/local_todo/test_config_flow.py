"""Test the local_todo config flow."""

from unittest.mock import AsyncMock

import pytest

from menuai import config_entries
from menuai.components.local_todo.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import STORAGE_KEY, TODO_NAME

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "todo_list_name": TODO_NAME,
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TODO_NAME
    assert result2["data"] == {
        "todo_list_name": TODO_NAME,
        "storage_key": STORAGE_KEY,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_todo_list_name(
    menuai: menuai, setup_integration: None, config_entry: MockConfigEntry
) -> None:
    """Test two todo-lists cannot be added with the same name."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result.get("errors")

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            # Pick a name that has the same slugify value as an existing config entry
            "todo_list_name": "my tasks",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
