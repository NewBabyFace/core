"""Tests for init platform of local_todo."""

from unittest.mock import patch

import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import TEST_ENTITY

from tests.common import MockConfigEntry


async def test_load_unload(
    menuai: menuai, setup_integration: None, config_entry: MockConfigEntry
) -> None:
    """Test loading and unloading a config entry."""

    assert config_entry.state is ConfigEntryState.LOADED

    state = menuai.states.get(TEST_ENTITY)
    assert state
    assert state.state == "0"

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    state = menuai.states.get(TEST_ENTITY)
    assert state
    assert state.state == "unavailable"


async def test_remove_config_entry(
    menuai: menuai, setup_integration: None, config_entry: MockConfigEntry
) -> None:
    """Test removing a config entry."""

    with patch("menuai.components.local_todo.Path.unlink") as unlink_mock:
        assert await menuai.config_entries.async_remove(config_entry.entry_id)
        await menuai.async_block_till_done()
        unlink_mock.assert_called_once()


@pytest.mark.parametrize(
    ("store_read_side_effect"),
    [
        (OSError("read error")),
    ],
)
async def test_load_failure(
    menuai: menuai, setup_integration: None, config_entry: MockConfigEntry
) -> None:
    """Test failures loading the todo store."""

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    state = menuai.states.get(TEST_ENTITY)
    assert not state
