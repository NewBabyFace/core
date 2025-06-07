"""Tests for the Enphase Envoy integration."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai,
    config_entry: MockConfigEntry,
    expected_state: ConfigEntryState = ConfigEntryState.LOADED,
) -> None:
    """Fixture for setting up the component and testing expected state."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert config_entry.state is expected_state
