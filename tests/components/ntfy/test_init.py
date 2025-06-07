"""Tests for the ntfy integration."""

from unittest.mock import AsyncMock

from aiontfy.exceptions import (
    NtfyConnectionError,
    NtfyHTTPError,
    NtfyTimeoutError,
    NtfyUnauthorizedAuthenticationError,
)
import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_aiontfy")
async def test_entry_setup_unload(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test integration setup and unload."""

    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("exception", "state"),
    [
        (
            NtfyUnauthorizedAuthenticationError(
                40101,
                401,
                "unauthorized",
                "https://ntfy.sh/docs/publish/#authentication",
            ),
            ConfigEntryState.SETUP_ERROR,
        ),
        (NtfyHTTPError(418001, 418, "I'm a teapot", ""), ConfigEntryState.SETUP_RETRY),
        (NtfyConnectionError, ConfigEntryState.SETUP_RETRY),
        (NtfyTimeoutError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_config_entry_not_ready(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_aiontfy: AsyncMock,
    exception: Exception,
    state: ConfigEntryState,
) -> None:
    """Test config entry not ready."""

    mock_aiontfy.account.side_effect = exception
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is state
