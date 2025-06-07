"""Tests for Glances integration."""

from unittest.mock import MagicMock

from glances_api.exceptions import (
    GlancesApiAuthorizationError,
    GlancesApiConnectionError,
    GlancesApiNoDataAvailable,
)
import pytest

from menuai.components.glances.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import MOCK_USER_INPUT

from tests.common import MockConfigEntry


async def test_successful_config_entry(menuai: menuai) -> None:
    """Test that Glances is configured successfully."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    ("error", "entry_state"),
    [
        (GlancesApiAuthorizationError, ConfigEntryState.SETUP_ERROR),
        (GlancesApiConnectionError, ConfigEntryState.SETUP_RETRY),
        (GlancesApiNoDataAvailable, ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_setup_error(
    menuai: menuai,
    error: Exception,
    entry_state: ConfigEntryState,
    mock_api: MagicMock,
) -> None:
    """Test Glances failed due to api error."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    mock_api.return_value.get_ha_sensor_data.side_effect = error
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is entry_state


async def test_unload_entry(menuai: menuai) -> None:
    """Test removing Glances."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert DOMAIN not in menuai.data
