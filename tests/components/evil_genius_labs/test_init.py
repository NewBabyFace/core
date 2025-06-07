"""Test evil genius labs init."""

import pytest

from menuai.components.evil_genius_labs import PLATFORMS
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai


@pytest.mark.parametrize("platforms", [PLATFORMS])
async def test_setup_unload_entry(
    menuai: menuai, setup_evil_genius_labs, config_entry
) -> None:
    """Test setting up and unloading a config entry."""
    assert len(menuai.states.async_entity_ids()) == 1
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
