"""Tests for the Rmenuaipy integration."""

from menuai.components.rmenuaipy.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(menuai: menuai) -> None:
    """Test the Rmenuaipy configuration entry loading/unloading."""
    mock_config_entry = MockConfigEntry(
        title="Rmenuaipy",
        domain=DOMAIN,
        data={},
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
