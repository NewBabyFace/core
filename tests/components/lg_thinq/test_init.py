"""Tests for the LG ThinQ integration."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_entry(
    menuai: menuai,
    mock_thinq_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test load and unload entry."""
    with patch(
        "menuai.components.lg_thinq.ThinQMQTT.async_connect",
        return_value=True,
    ):
        await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_remove(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("exception", [AttributeError(), TypeError(), ValueError()])
async def test_config_not_ready(
    menuai: menuai,
    mock_thinq_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
) -> None:
    """Test for setup failure exception occurred."""
    with patch(
        "menuai.components.lg_thinq.ThinQMQTT.async_connect",
        side_effect=exception,
    ):
        await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
