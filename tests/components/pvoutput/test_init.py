"""Tests for the PVOutput integration."""

from unittest.mock import MagicMock

from pvo import (
    PVOutputAuthenticationError,
    PVOutputConnectionError,
    PVOutputNoDataError,
)
import pytest

from menuai.components.pvoutput.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
) -> None:
    """Test the PVOutput configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert len(mock_pvoutput.status.mock_calls) == 1
    assert len(mock_pvoutput.system.mock_calls) == 1

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize("side_effect", [PVOutputConnectionError, PVOutputNoDataError])
async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
    side_effect: Exception,
) -> None:
    """Test the PVOutput configuration entry not ready."""
    mock_pvoutput.status.side_effect = side_effect

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert len(mock_pvoutput.status.mock_calls) == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_entry_authentication_failed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput: MagicMock,
) -> None:
    """Test trigger reauthentication flow."""
    mock_config_entry.add_to_menuai(menuai)

    mock_pvoutput.status.side_effect = PVOutputAuthenticationError

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == mock_config_entry.entry_id
