"""Test init of Brother integration."""

from unittest.mock import AsyncMock, patch

from brother import SnmpError
import pytest

from menuai.components.brother.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_integration

from tests.common import MockConfigEntry


async def test_async_setup_entry(
    menuai: menuai,
    mock_brother_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test a successful setup entry."""
    await init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_config_not_ready(
    menuai: menuai,
    mock_brother_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test for setup failure if connection to broker is missing."""
    mock_brother_client.async_update.side_effect = ConnectionError

    await init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("exc", [(SnmpError("SNMP Error")), (ConnectionError)])
async def test_error_on_init(
    menuai: menuai, exc: Exception, mock_config_entry: MockConfigEntry
) -> None:
    """Test for error on init."""
    with patch(
        "menuai.components.brother.Brother.create",
        new=AsyncMock(side_effect=exc),
    ):
        await init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    menuai: menuai,
    mock_brother_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful unload of entry."""
    await init_integration(menuai, mock_config_entry)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
