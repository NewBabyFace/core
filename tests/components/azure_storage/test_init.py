"""Test the Azure storage integration."""

from unittest.mock import MagicMock

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the integration."""
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("exception", "state"),
    [
        (ClientAuthenticationError, ConfigEntryState.SETUP_ERROR),
        (HttpResponseError, ConfigEntryState.SETUP_RETRY),
        (ResourceNotFoundError, ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_setup_errors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    exception: Exception,
    state: ConfigEntryState,
) -> None:
    """Test various setup errors."""
    mock_client.exists.side_effect = exception()
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is state
