"""Tests for the CPU Speed integration."""

from unittest.mock import MagicMock

import pytest

from menuai.components.cpuspeed.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_cpuinfo: MagicMock,
) -> None:
    """Test the CPU Speed configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert len(mock_cpuinfo.mock_calls) == 2

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_config_entry_not_compatible(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_cpuinfo: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the CPU Speed configuration entry loading on an unsupported system."""
    mock_config_entry.add_to_menuai(menuai)
    mock_cpuinfo.return_value = {}

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(mock_cpuinfo.mock_calls) == 1
    assert "is not compatible with your system" in caplog.text
