"""Test bluesound integration."""

from pyblu.errors import PlayerUnreachableError

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import PlayerMocks

from tests.common import MockConfigEntry


async def test_setup_entry(
    menuai: menuai, setup_config_entry: None, config_entry: MockConfigEntry
) -> None:
    """Test a successful setup entry."""
    assert menuai.states.get("media_player.player_name1111").state == "playing"
    assert config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("media_player.player_name1111").state == "unavailable"
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_unload_entry_while_player_is_offline(
    menuai: menuai,
    setup_config_entry: None,
    config_entry: MockConfigEntry,
    player_mocks: PlayerMocks,
) -> None:
    """Test entries can be unloaded correctly while the player is offline."""
    player_mocks.player_data.player.status.side_effect = PlayerUnreachableError(
        "Player not reachable"
    )
    player_mocks.player_data.status_long_polling_mock.trigger()

    # give the long polling loop a chance to update the state; this could be any async call
    await menuai.async_block_till_done()

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("media_player.player_name1111").state == "unavailable"
    assert config_entry.state is ConfigEntryState.NOT_LOADED
