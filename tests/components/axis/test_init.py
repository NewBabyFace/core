"""Test Axis component setup process."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from menuai.components import axis
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_setup_entry(config_entry_setup: MockConfigEntry) -> None:
    """Test successful setup of entry."""
    assert config_entry_setup.state is ConfigEntryState.LOADED


async def test_setup_entry_fails(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test successful setup of entry."""
    config_entry.add_to_menuai(menuai)

    mock_device = Mock()
    mock_device.async_setup = AsyncMock(return_value=False)

    with patch.object(axis, "AxisHub") as mock_device_class:
        mock_device_class.return_value = mock_device

        assert not await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(
    menuai: menuai, config_entry_setup: MockConfigEntry
) -> None:
    """Test successful unload of entry."""
    assert config_entry_setup.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(config_entry_setup.entry_id)
    assert config_entry_setup.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("config_entry_version", [1])
async def test_migrate_entry(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test successful migration of entry data."""
    config_entry.add_to_menuai(menuai)
    assert config_entry.version == 1

    mock_device = Mock()
    mock_device.async_setup = AsyncMock()
    mock_device.async_update_device_registry = AsyncMock()
    mock_device.api.vapix.light_control = None
    mock_device.api.vapix.params.image_format = None

    with patch("menuai.components.axis.async_setup_entry", return_value=True):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.version == 3
