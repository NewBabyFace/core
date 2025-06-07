"""Unit tests for the Todoist integration."""

from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest

from menuai.components.todoist.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload(
    menuai: menuai,
    setup_integration: None,
    todoist_config_entry: MockConfigEntry | None,
) -> None:
    """Test loading and unloading of the config entry."""
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    assert todoist_config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(todoist_config_entry.entry_id)
    assert todoist_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("todoist_api_status", [HTTPStatus.INTERNAL_SERVER_ERROR])
async def test_init_failure(
    menuai: menuai,
    setup_integration: None,
    api: AsyncMock,
    todoist_config_entry: MockConfigEntry | None,
) -> None:
    """Test an initialization error on integration load."""
    assert todoist_config_entry.state is ConfigEntryState.SETUP_RETRY
